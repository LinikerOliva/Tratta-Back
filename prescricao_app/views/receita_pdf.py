"""
prescricao_app/views/receita_pdf.py
Endpoint para geração de PDF da receita médica via WeasyPrint.

Rota:  GET /api/receitas/{id}/pdf/
Acesso: médico dono da receita, admin, ou paciente dono da receita.
"""
import io
import logging
from datetime import date

from django.http import HttpResponse
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from prescricao_app.models import Receita
from trathea_core.utils.response import api_not_found, api_error

logger = logging.getLogger("trathea")


def _gerar_pdf_bytes(receita: Receita) -> bytes:
    """
    Renderiza o template HTML da receita e converte para PDF com WeasyPrint.
    Monta um contexto enriquecido compatível com o template existente.
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError(
            "WeasyPrint não está instalado. "
            "Execute: pip install weasyprint  "
            "(no servidor Linux, instale também: "
            "apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0)"
        )

    # ── Monta contexto compatível com o template templates/pdf/receita.html ──
    itens = []
    for item in receita.itens.select_related("medicamento").order_by("ordem", "id"):
        itens.append(
            {
                "nome": item.medicamento.nome,
                "principio_ativo": item.medicamento.principio_ativo,
                "dosagem": item.dosagem,
                "posologia": item.posologia,
                "quantidade": item.quantidade,
                "duracao": item.duracao_tratamento,
                "via": item.via_administracao,
            }
        )

    medico = receita.medico
    paciente = receita.paciente

    contexto = {
        "receita": {
            "id": receita.id,
            "tipo": receita.tipo,
            "status": receita.status,
            "data_emissao": receita.data_emissao.strftime("%d/%m/%Y") if receita.data_emissao else "—",
            "observacoes": receita.observacoes,
            "hash_verificacao": receita.hash_verificacao or "",
            "via_govbr": receita.via_govbr,
            "ano": date.today().year,
            "medico": {
                "nome": getattr(medico, "nome_completo", str(medico)),
                "especialidade": getattr(medico, "especialidade", ""),
                "crm": getattr(medico, "crm", ""),
                "crm_estado": getattr(medico, "crm_estado", ""),
            },
            "paciente": {
                "nome": getattr(paciente, "nome_completo", str(paciente)),
                "cpf": getattr(paciente, "cpf", ""),
                "data_nascimento": (
                    paciente.data_nascimento.strftime("%d/%m/%Y")
                    if getattr(paciente, "data_nascimento", None)
                    else "—"
                ),
            },
            "itens": itens,
        }
    }

    html_str = render_to_string("pdf/receita.html", contexto)
    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes


class ReceitaPDFView(APIView):
    """
    GET /api/receitas/{id}/pdf/
    Retorna o PDF da receita médica como download (application/pdf).

    Permissões:
    - Médico: apenas receitas próprias
    - Paciente: apenas receitas suas
    - Admin: qualquer receita
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Receitas"],
        summary="Download do PDF da receita",
        description=(
            "Gera e retorna o PDF da receita médica. "
            "Médico acessa apenas suas próprias receitas; "
            "paciente acessa apenas as suas; admin acessa qualquer uma."
        ),
        responses={
            200: OpenApiResponse(description="PDF gerado (application/pdf)."),
            403: OpenApiResponse(description="Sem permissão para acessar esta receita."),
            404: OpenApiResponse(description="Receita não encontrada."),
            500: OpenApiResponse(description="Erro ao gerar o PDF."),
        },
    )
    def get(self, request, pk):
        # ── Busca a receita ───────────────────────────────────────────────────
        try:
            receita = (
                Receita.objects
                .select_related("medico__user", "paciente__user")
                .prefetch_related("itens__medicamento")
                .get(pk=pk)
            )
        except Receita.DoesNotExist:
            return api_not_found("Receita não encontrada.")

        # ── RBAC ─────────────────────────────────────────────────────────────
        user = request.user
        if user.role == "medico" and receita.medico.user != user:
            return api_error("Você não tem acesso a esta receita.", http_status=403)
        if user.role == "paciente" and receita.paciente.user != user:
            return api_error("Você não tem acesso a esta receita.", http_status=403)
        if user.role not in ("medico", "paciente", "admin"):
            return api_error("Acesso negado.", http_status=403)

        # ── Gera o PDF ───────────────────────────────────────────────────────
        try:
            pdf_bytes = _gerar_pdf_bytes(receita)
        except ImportError as exc:
            logger.error("WeasyPrint não instalado: %s", exc)
            return api_error(
                "Geração de PDF indisponível no momento. "
                "Contate o administrador do sistema.",
                http_status=500,
            )
        except Exception as exc:
            logger.exception("Erro ao gerar PDF da receita #%s: %s", pk, exc)
            return api_error("Erro interno ao gerar o PDF.", http_status=500)

        # ── Retorna o arquivo ─────────────────────────────────────────────────
        nome_arquivo = f"receita_{receita.id}_{receita.paciente.user.username}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
        response["Content-Length"] = len(pdf_bytes)
        return response
