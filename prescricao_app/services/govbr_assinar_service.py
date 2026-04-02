"""
prescricao_app/services/govbr_assinar_service.py
Serviço que orquestra o fluxo completo de assinatura digital via Gov.br.

Fluxo:
1. Serializar conteúdo canônico da receita
2. Calcular hash SHA-256
3. Gerar PDF da receita
4. Enviar hash para a API Gov.br → receber PAdES
5. Acoplar PAdES ao PDF (modo dev: retorna PDF sem acoplamento)
6. Salvar PDF assinado e atualizar status da receita
7. Registrar auditoria

PRINCÍPIO: Toda a lógica de negócio fica aqui — NUNCA na view.
"""
import logging
from datetime import datetime

from django.utils import timezone
from django.core.files.base import ContentFile

from trathea_core.signature.hash_utils import gerar_hash_conteudo, gerar_hash_pdf, gerar_hash_verificacao
from trathea_core.signature.govbr_oauth import GovBrOAuthService
from trathea_core.signature.govbr_signature import GovBrSignatureService, GovBrSignatureError
from trathea_core.pdf.pdf_generator import gerar_pdf_receita, PDFGenerationError
from trathea_core.audit.audit import log_audit
from trathea_core.audit.models import LogAuditoria

logger = logging.getLogger("trathea")


class GovBrAssinarService:
    """
    Serviço de assinatura de receitas via Gov.br.

    Uso:
        service = GovBrAssinarService()
        resultado = service.assinar_receita(receita=receita, request=request)
    """

    def __init__(self):
        self._oauth_service = GovBrOAuthService()
        self._signature_service = GovBrSignatureService()

    def assinar_receita(self, receita, request) -> dict:
        """
        Executa o fluxo completo de assinatura de uma receita.

        Args:
            receita: Instância de Receita a ser assinada.
            request: Request DRF para auditoria e token Gov.br.

        Returns:
            Dicionário com pdf_url, hash_verificacao e status.

        Raises:
            ReceitaJaAssinadaError: Se a receita já foi assinada.
            MedicoNaoVinculadoError: Se o médico não vinculou o Gov.br.
            GovBrSignatureError: Se o Gov.br retornar erro.
        """
        medico = receita.medico

        # ── Validações de negócio ──────────────────────────────────────────────
        if receita.status == "assinada":
            raise ReceitaJaAssinadaError("Esta receita já foi assinada digitalmente.")

        if not receita.pode_ser_assinada:
            raise ReceitaNaoPodeSerAssinadaError(
                f"Receita com status '{receita.status}' não pode ser assinada."
            )

        if not medico.is_govbr_linked:
            raise MedicoNaoVinculadoError(
                "Você precisa vincular sua conta ao Gov.br antes de assinar receitas. "
                "Acesse: /api/auth/govbr/authorize/"
            )

        # ── PASSO 1: Serializar conteúdo canônico ────────────────────────────
        from prescricao_app.serializers import ReceitaSerializer
        conteudo_canonico = self._serializar_conteudo_canonico(receita)

        # ── PASSO 2: Calcular hash do conteúdo ───────────────────────────────
        hash_conteudo = gerar_hash_conteudo(conteudo_canonico)
        logger.info(f"Hash do conteúdo da receita #{receita.id}: {hash_conteudo[:16]}...")

        # ── PASSO 3: Gerar PDF ────────────────────────────────────────────────
        try:
            pdf_bytes = gerar_pdf_receita(conteudo_canonico)
        except PDFGenerationError as e:
            raise AssinaturaError(f"Falha ao gerar PDF: {e}")

        # ── PASSO 4: Obter token Gov.br do médico e solicitar assinatura ──────
        # Para a API de assinatura, usamos o access_token do Gov.br vinculado
        # Em produção, este token deve ser armazenado/renovado de forma segura
        govbr_token = self._obter_token_govbr(medico)

        try:
            assinatura_pades = self._signature_service.solicitar_assinatura_hash(
                hash_documento=gerar_hash_pdf(pdf_bytes),
                access_token=govbr_token,
            )
        except GovBrSignatureError:
            raise  # Propaga para a view tratar corretamente

        # ── PASSO 5: Acoplar PAdES ao PDF ────────────────────────────────────
        pdf_assinado = self._acoplar_pades_ao_pdf(pdf_bytes, assinatura_pades)

        # ── PASSO 6: Gerar hash de verificação pública ────────────────────────
        hash_verificacao = gerar_hash_verificacao()

        # ── PASSO 7: Salvar PDF e atualizar receita ──────────────────────────
        nome_arquivo = f"receita_{receita.id}_{hash_verificacao[:8]}.pdf"
        receita.pdf.save(nome_arquivo, ContentFile(pdf_assinado), save=False)
        receita.hash_conteudo = hash_conteudo
        receita.hash_verificacao = hash_verificacao
        receita.assinatura_govbr = assinatura_pades
        receita.via_govbr = True
        receita.status = "assinada"
        receita.assinada_em = timezone.now()
        receita.save(update_fields=[
            "pdf", "hash_conteudo", "hash_verificacao",
            "assinatura_govbr", "via_govbr", "status", "assinada_em",
        ])

        # ── PASSO 8: Auditoria ────────────────────────────────────────────────
        log_audit(
            request=request,
            acao=LogAuditoria.Acao.ASSINAR_RECEITA,
            modelo="Receita",
            pk_objeto=str(receita.id),
            dados_extra={
                "hash_conteudo": hash_conteudo,
                "hash_verificacao": hash_verificacao,
                "via_govbr": True,
                "medico_crm": medico.crm,
                "paciente_id": str(receita.paciente_id),
            },
        )

        logger.info(f"Receita #{receita.id} assinada digitalmente via Gov.br.")

        return {
            "receita_id": receita.id,
            "status": receita.status,
            "pdf_url": receita.pdf.url if receita.pdf else None,
            "hash_verificacao": hash_verificacao,
            "assinada_em": receita.assinada_em.isoformat(),
            "verificacao_url": f"/verificar/{hash_verificacao}/",
        }

    def _serializar_conteudo_canonico(self, receita) -> dict:
        """Serializa a receita em formato canônico para o hash."""
        itens = [
            {
                "medicamento": item.medicamento.nome,
                "principio_ativo": item.medicamento.principio_ativo,
                "dosagem": item.dosagem,
                "quantidade": item.quantidade,
                "posologia": item.posologia,
                "via": item.via_administracao,
                "duracao": item.duracao_tratamento,
            }
            for item in receita.itens.select_related("medicamento").order_by("ordem")
        ]

        return {
            "id": receita.id,
            "tipo": receita.tipo,
            "data_emissao": receita.data_emissao.isoformat(),
            "medico": {
                "nome": receita.medico.user.nome_completo,
                "crm": receita.medico.crm,
                "crm_estado": receita.medico.crm_estado,
                "especialidade": receita.medico.especialidade,
            },
            "paciente": {
                "nome": receita.paciente.user.nome_completo,
                "cpf": receita.paciente.user.profile.cpf,
                "data_nascimento": str(receita.paciente.data_nascimento),
            },
            "itens": itens,
            "observacoes": receita.observacoes,
        }

    def _obter_token_govbr(self, medico) -> str:
        """
        Obtém o token Gov.br do médico.
        Em produção: buscar do cache/banco e renovar se expirado.
        """
        # TODO: Implementar cache/persistência segura do token Gov.br
        # Por enquanto retorna string vazia para testes (staging Gov.br)
        return ""

    def _acoplar_pades_ao_pdf(self, pdf_bytes: bytes, assinatura: bytes) -> bytes:
        """
        Acopla a assinatura PAdES ao PDF.
        Em ambiente de desenvolvimento, retorna o PDF original sem acoplamento.
        Para produção, implemente com uma biblioteca compatível com o ambiente de destino.
        """
        logger.warning(
            "PAdES acoplamento: modo desenvolvimento — PDF retornado sem assinatura acoplada. "
            "Para produção, configure um serviço de assinatura PAdES compatível."
        )
        return pdf_bytes


# ── Exceções de Domínio ───────────────────────────────────────────────────────
class AssinaturaError(Exception):
    """Erro genérico no processo de assinatura."""
    pass


class ReceitaJaAssinadaError(AssinaturaError):
    """Receita já possui assinatura digital."""
    pass


class ReceitaNaoPodeSerAssinadaError(AssinaturaError):
    """Status da receita não permite assinatura."""
    pass


class MedicoNaoVinculadoError(AssinaturaError):
    """Médico não vinculou conta ao Gov.br."""
    pass
