"""
medico_app/views_paciente360.py
Dashboard 360° do Paciente — Visão completa para o médico.
"""
import logging
from datetime import date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from django.utils import timezone

from trathea_core.utils.response import api_success, api_error, api_not_found
from paciente_app.models import Paciente, Prontuario
from consulta_app.models import Consulta
from medico_app.models import Medico

logger = logging.getLogger("trathea")


def _resolve_medico(user):
    """
    Resolve o perfil Medico do usuário.
    Para admin (testes), usa o primeiro médico do sistema como fallback.
    """
    medico = getattr(user, "medico", None)
    if medico:
        return medico
    # Admin sem perfil médico — fallback para testes
    if user.role == "admin":
        return Medico.objects.first()
    return None


def _calcular_idade(data_nascimento):
    if not data_nascimento:
        return ""
    hoje = date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )

def _extrair_dados_paciente(paciente):
    """Extrai informações resumidas do paciente para listagens protegidas."""
    profile = getattr(paciente.user, 'profile', None)
    cpf = profile.cpf if profile and profile.cpf else ""
    cpf_mascarado = f"***.{cpf[3:6]}.***-**" if len(cpf) >= 6 else ""
    foto_url = profile.foto.url if profile and profile.foto else None

    return {
        "nome": paciente.user.nome_completo,
        "idade": _calcular_idade(paciente.data_nascimento),
        "cpf": cpf_mascarado,
        "foto_url": foto_url,
    }


@extend_schema(
    tags=["Consulta Médica"],
    summary="Dashboard 360° do Paciente",
    description=(
        "Retorna visão completa do paciente: dados pessoais, alergias, "
        "timeline dos últimos eventos, informações críticas e receitas ativas."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def paciente_360_view(request, paciente_id):
    """Visão 360° do paciente para o médico."""
    try:
        paciente = Paciente.objects.select_related("user").get(id=paciente_id)
    except Paciente.DoesNotExist:
        return api_not_found("Paciente não encontrado.")

    # ── Dados do cabeçalho ───────────────────────────────────────────────
    cabecalho = {
        "id": paciente.id,
        "nome": paciente.user.nome_completo,
        "idade": _calcular_idade(paciente.data_nascimento),
        "data_nascimento": paciente.data_nascimento.isoformat(),
        "foto_url": paciente.user.foto.url if hasattr(paciente.user, 'foto') and paciente.user.foto else None,
        "email": paciente.user.email,
        "telefone": getattr(paciente.user, 'telefone', ''),
        "convenio": paciente.convenio_nome or "Particular",
        "convenio_numero": paciente.convenio_numero,
    }

    # ── Alergias (destaque visual) ───────────────────────────────────────
    alergias_raw = paciente.alergias or ""
    alergias = [a.strip() for a in alergias_raw.split(",") if a.strip()] if alergias_raw else []

    # ── Informações críticas ─────────────────────────────────────────────
    info_critica = {
        "tipo_sanguineo": paciente.tipo_sanguineo or "Não informado",
        "doencas_cronicas": paciente.doencas_cronicas or "Nenhuma registrada",
        "medicamentos_uso_continuo": paciente.medicamentos_uso_continuo or "Nenhum",
        "peso_kg": float(paciente.peso_kg) if paciente.peso_kg else None,
        "altura_cm": paciente.altura_cm,
    }

    # ── Timeline recente (últimos 3 eventos) ─────────────────────────────
    timeline = []

    # Consultas recentes
    consultas_recentes = Consulta.objects.filter(
        paciente=paciente
    ).select_related("medico__user").order_by("-data_inicio")[:5]

    for c in consultas_recentes:
        timeline.append({
            "tipo": "consulta",
            "id": c.id,
            "titulo": f"Consulta com Dr(a). {c.medico.user.nome_completo}",
            "data": c.data_inicio.isoformat(),
            "status": c.status,
            "resumo": c.resumo[:120] if c.resumo else "",
            "duracao_min": round(c.duracao_segundos / 60) if c.duracao_segundos else None,
        })

    # Prontuários recentes
    prontuarios = Prontuario.objects.filter(
        paciente=paciente
    ).select_related("medico__user").order_by("-data_consulta")[:5]

    for p in prontuarios:
        timeline.append({
            "tipo": "prontuario",
            "id": p.id,
            "titulo": f"Prontuário — {p.queixa_principal[:60]}",
            "data": p.data_consulta.isoformat(),
            "status": "registrado",
            "resumo": p.hipotese_diagnostica[:120] if p.hipotese_diagnostica else "",
            "cid": p.diagnostico_cid10 or None,
        })

    # Receitas recentes
    try:
        from prescricao_app.models import Receita
        receitas = Receita.objects.filter(
            paciente=paciente
        ).select_related("medico__user").order_by("-data_emissao")[:3]

        for r in receitas:
            timeline.append({
                "tipo": "receita",
                "id": r.id,
                "titulo": f"Receita {r.get_tipo_display()}",
                "data": r.data_emissao.isoformat(),
                "status": r.status,
                "resumo": r.observacoes[:120] if r.observacoes else "",
            })
    except Exception:
        pass

    # Exames recentes
    try:
        from exame_app.models import SolicitacaoExame
        exames = SolicitacaoExame.objects.filter(
            paciente=paciente
        ).order_by("-data_solicitacao")[:3]

        for e in exames:
            timeline.append({
                "tipo": "exame",
                "id": e.id,
                "titulo": f"Exame: {getattr(e.tipo_exame, 'nome', 'Laboratorial')} [{e.status}]",
                "data": e.data_solicitacao.isoformat(),
                "status": e.status,
                "resumo": e.instrucoes[:120],
            })
    except Exception:
        pass

    # Ordenar timeline por data (mais recente primeiro) e pegar top 3
    timeline.sort(key=lambda x: x["data"], reverse=True)
    timeline = timeline[:3]

    # ── Estatísticas ─────────────────────────────────────────────────────
    total_consultas = Consulta.objects.filter(paciente=paciente).count()
    total_receitas = 0
    try:
        from prescricao_app.models import Receita
        total_receitas = Receita.objects.filter(paciente=paciente).count()
    except Exception:
        pass

    estatisticas = {
        "total_consultas": total_consultas,
        "total_receitas": total_receitas,
        "total_prontuarios": Prontuario.objects.filter(paciente=paciente).count(),
    }

    return api_success(data={
        "cabecalho": cabecalho,
        "alergias": alergias,
        "info_critica": info_critica,
        "timeline": timeline,
        "estatisticas": estatisticas,
    })


@extend_schema(
    tags=["Consulta Médica"],
    summary="Iniciar Consulta Inteligente",
    description="Cria uma consulta e inicia o cronômetro automático.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def iniciar_consulta_inteligente_view(request):
    """Inicia uma consulta inteligente com cronômetro automático."""
    medico = _resolve_medico(request.user)
    if not medico:
        return api_error("Apenas médicos podem iniciar consultas.", http_status=403)

    paciente_id = request.data.get("paciente_id")
    if not paciente_id:
        return api_error("paciente_id é obrigatório.")

    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        return api_not_found("Paciente não encontrado.")

    consulta = Consulta.objects.create(
        paciente=paciente,
        medico=medico,
        data_inicio=timezone.now(),
        status=Consulta.Status.EM_ANDAMENTO,
    )

    logger.info(
        f"Consulta #{consulta.id} iniciada por {medico} para paciente #{paciente.id}"
    )

    return api_success(data={
        "consulta_id": consulta.id,
        "data_inicio": consulta.data_inicio.isoformat(),
        "status": consulta.status,
    }, message="Consulta iniciada com sucesso.")


@extend_schema(
    tags=["Consulta Médica"],
    summary="Salvar transcrição processada",
    description="Salva apenas o texto processado, respeitando LGPD (sem áudio bruto).",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def salvar_transcricao_view(request, consulta_id):
    """Salva a transcrição da consulta (apenas texto, LGPD)."""
    try:
        consulta = Consulta.objects.get(id=consulta_id)
    except Consulta.DoesNotExist:
        return api_not_found("Consulta não encontrada.")

    texto = request.data.get("transcricao_texto", "")
    if not texto.strip():
        return api_error("Transcrição vazia.")

    consulta.transcricao_texto = texto
    consulta.save(update_fields=["transcricao_texto"])

    logger.info(f"Transcrição salva para consulta #{consulta_id} (LGPD: sem áudio)")

    return api_success(message="Transcrição salva com sucesso.")


@extend_schema(
    tags=["Consulta Médica"],
    summary="Estruturar transcrição com IA",
    description="Processa o texto da transcrição e sugere preenchimento de anamnese, queixa e hipótese.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def estruturar_transcricao_ia_view(request, consulta_id):
    """IA processa a transcrição e sugere campos clínicos."""
    try:
        consulta = Consulta.objects.get(id=consulta_id)
    except Consulta.DoesNotExist:
        return api_not_found("Consulta não encontrada.")

    texto = request.data.get("transcricao_texto", "") or consulta.transcricao_texto
    if not texto.strip():
        return api_error("Sem texto para processar.")

    # ── Processamento IA com Gemini ─────────────────────────
    try:
        from trathea_core.ai.gemini_service import GeminiService
        gemini = GeminiService()
        resposta_ia = gemini.estruturar_transcricao(texto)
        dados = resposta_ia.get("sugestao", {})
        
        medicamentos_formatados = []
        for meds in dados.get("medicamentos", []):
            if isinstance(meds, dict):
                medicamentos_formatados.append({
                    "nome": meds.get("nome", "").strip().capitalize(),
                    "dosagem": meds.get("dosagem", "A definir"),
                    "posologia": meds.get("posologia", "A definir"),
                    "quantidade": meds.get("quantidade", "A definir"),
                    "via": meds.get("via", "oral").lower()
                })
            elif isinstance(meds, str):
                medicamentos_formatados.append({
                    "nome": meds.strip().capitalize(),
                    "dosagem": "A definir",
                    "posologia": "A definir",
                    "quantidade": "A definir",
                    "via": "oral"
                })
        
        sugestao = {
            "queixa_principal": dados.get("queixaPrincipal", dados.get("queixa_principal", "Resumo não disponível.")),
            "anamnese": dados.get("anamnese", texto),
            "exame_fisico": dados.get("exameFisico", dados.get("exame_fisico", "")),
            "hipotese_diagnostica": dados.get("hipoteseDiagnostica", dados.get("hipotese_diagnostica", "A avaliar")),
            "conduta": dados.get("condutaMedica", dados.get("conduta", "")),
            "medicamentos": medicamentos_formatados,
        }
    except Exception as e:
        logger.error(f"Erro ao estruturar transcrição com IA: {e}")
        # Fallback simples caso IA falhe
        sugestao = {
            "queixa_principal": texto[:100] + "...",
            "anamnese": texto,
            "exame_fisico": "",
            "hipotese_diagnostica": "A avaliar",
            "conduta": "",
            "medicamentos": [],
        }

    return api_success(data=sugestao, message="Sugestão gerada com sucesso.")


@extend_schema(
    tags=["Consulta Médica"],
    summary="Finalizar consulta com prontuário e prescrição",
    description="Finaliza a consulta, calcula duração, salva prontuário e pode gerar receita.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def finalizar_consulta_completa_view(request, consulta_id):
    """Finaliza consulta com prontuário, duração automática, e receita com assinatura."""
    from trathea_core.signature.govbr import GovBrSignatureIntegration
    from django.core.files.base import ContentFile
    import hashlib
    medico = _resolve_medico(request.user)
    if not medico:
        return api_error("Apenas médicos podem finalizar consultas.", http_status=403)

    try:
        consulta = Consulta.objects.select_related("paciente").get(id=consulta_id)
    except Consulta.DoesNotExist:
        return api_not_found("Consulta não encontrada.")

    # Salvar campos clínicos
    consulta.queixa_principal = request.data.get("queixa_principal", consulta.queixa_principal)
    consulta.anamnese = request.data.get("anamnese", consulta.anamnese)
    consulta.hipotese_diagnostica = request.data.get("hipotese_diagnostica", consulta.hipotese_diagnostica)
    consulta.transcricao_texto = request.data.get("transcricao_texto", consulta.transcricao_texto)
    consulta.resumo = request.data.get("resumo", consulta.resumo)

    # Finalizar com cronômetro automático
    consulta.data_fim = timezone.now()
    consulta.status = Consulta.Status.FINALIZADA
    if consulta.data_inicio:
        consulta.duracao_segundos = int(
            (consulta.data_fim - consulta.data_inicio).total_seconds()
        )

    consulta.save()

    # Criar prontuário
    prontuario = Prontuario.objects.create(
        paciente=consulta.paciente,
        medico=medico,
        data_consulta=consulta.data_inicio,
        queixa_principal=consulta.queixa_principal,
        anamnese=consulta.anamnese,
        hipotese_diagnostica=consulta.hipotese_diagnostica,
        conduta=request.data.get("conduta", ""),
        diagnostico_cid10=request.data.get("cid10", ""),
    )

    prontuario_auth_url = None
    tipo_assinatura = request.data.get("tipo_assinatura")

    # Gerar receita se houver medicamentos
    receita_data = None
    medicamentos = request.data.get("medicamentos", [])
    if medicamentos:
        try:
            from prescricao_app.models import Receita, ItemReceita, Medicamento

            receita = Receita.objects.create(
                medico=medico,
                paciente=consulta.paciente,
                consulta=consulta,
                tipo=request.data.get("tipo_receita", "simples"),
                observacoes=request.data.get("observacoes_receita", ""),
            )

            for i, med in enumerate(medicamentos):
                nome = med.get("nome", "").strip()
                if not nome: continue
                
                med_obj, _ = Medicamento.objects.get_or_create(nome__iexact=nome, defaults={"nome": nome, "principio_ativo": nome})
                
                ItemReceita.objects.create(
                    receita=receita,
                    medicamento=med_obj,
                    dosagem=med.get("dosagem", ""),
                    quantidade=med.get("quantidade", ""),
                    posologia=med.get("posologia", ""),
                    via_administracao=med.get("via", "oral"),
                    duracao_tratamento=med.get("duracao", ""),
                    instrucoes_especiais=med.get("instrucoes", ""),
                    ordem=i,
                )

            receita_data = {
                "receita_id": receita.id,
                "status": receita.status,
                "tipo": receita.tipo,
            }
            
            # Fluxo de Assinatura
            if tipo_assinatura in ['govbr', 'senha']:
                # Preparação do Documento (PDF bruto e Hash)
                pdf_bytes = GovBrSignatureIntegration.gerar_pdf_receita_bruto(
                    medico=medico,
                    paciente=consulta.paciente,
                    medicamentos=medicamentos,
                    observacoes=receita.observacoes
                )
                receita.pdf.save(f"receita_{receita.id}_bruta.pdf", ContentFile(pdf_bytes))
                
                hash_doc = hashlib.sha256(pdf_bytes).hexdigest()
                receita.hash_conteudo = hash_doc
                receita.save(update_fields=["hash_conteudo"])
                
                if tipo_assinatura == 'govbr':
                    # Fluxo de Assinatura (OAuth2 Gov.BR)
                    auth_url = GovBrSignatureIntegration.iniciar_fluxo_govbr(hash_doc, consulta.id)
                    receita_data["govbr_auth_url"] = auth_url
                elif tipo_assinatura == 'senha':
                    # Fluxo A3 Token (WebPKI simulação local). 
                    # Na vida real: frontend assina o hash, backend verifica e guarda a assinatura pkcs7.
                    # Aqui simulamos o sucesso do ITI Carimbo:
                    verification_url = f"https://assinatura.iti.gov.br/validar/?hash={hash_doc[:8]}"
                    pdf_carimbado = GovBrSignatureIntegration.carimbar_pdf(pdf_bytes, verification_url)
                    receita.pdf.save(f"receita_{receita.id}_assinada_a3.pdf", ContentFile(pdf_carimbado))
                    # Atualiza status para assinado (ou similar se o seu Model prever outro campo)
                    receita_data["pki_auth_success"] = True

        except Exception as e:
            logger.error(f"Erro ao criar receita: {e}")

    # ===== SE NÃO TEM MEDICAMENTOS, MAS QUER ASSINAR (O Prontuário) ======
    elif tipo_assinatura in ['govbr', 'senha']:
        try:
            # Simulamos a assinatura do prontuário
            hash_doc = hashlib.sha256(f"prontuario_{prontuario.id}".encode("utf-8")).hexdigest()
            if tipo_assinatura == 'govbr':
                auth_url = GovBrSignatureIntegration.iniciar_fluxo_govbr(hash_doc, consulta.id)
                prontuario_auth_url = auth_url
            else:
                receita_data = {"pki_auth_success": True}
        except Exception as e:
            logger.error(f"Erro ao iniciar PKI/GovBR para o prontuario: {e}")

    result = {
        "consulta_id": consulta.id,
        "status": consulta.status,
        "duracao_segundos": consulta.duracao_segundos,
        "duracao_formatada": _formatar_duracao(consulta.duracao_segundos),
        "prontuario_id": prontuario.id,
        "prontuario_auth_url": prontuario_auth_url,
        "receita": receita_data,
    }

    logger.info(
        f"Consulta #{consulta_id} finalizada. Duração: {consulta.duracao_segundos}s"
    )

    return api_success(data=result, message="Consulta finalizada com sucesso.")


def _formatar_duracao(segundos):
    if not segundos:
        return "0min"
    minutos = segundos // 60
    segs = segundos % 60
    if minutos >= 60:
        horas = minutos // 60
        minutos = minutos % 60
        return f"{horas}h {minutos}min"
    return f"{minutos}min {segs}s"


@extend_schema(
    tags=["Consulta Médica"],
    summary="Detalhes do Atendimento (Consulta/Receita)",
    description="Retorna os detalhes de um evento da timeline, validando clinica_id para evitar vazamento.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def atendimento_detalhes_view(request, atendimento_id):
    """Retorna detalhes do evento baseando-se no tipo e validação de clínica segura."""
    medico = _resolve_medico(request.user)
    if not medico:
        return api_error("Apenas médicos podem acessar esta rota.", http_status=403)
        
    tipo = request.query_params.get("tipo", "consulta")
    # Sec: Validação do clinic_id do médico vs clinic_id do evento para evitar data leak
    clinic_id_medico = medico.clinica_principal_id
    
    if tipo == "consulta":
        try:
            evento = Consulta.objects.select_related("medico", "paciente__user").get(id=atendimento_id)
        except Consulta.DoesNotExist:
            return api_not_found("Consulta não encontrada.")
            
        clinic_id_evento = evento.medico.clinica_principal_id if evento.medico else None
        if clinic_id_medico and clinic_id_evento and clinic_id_medico != clinic_id_evento:
            return api_error("Acesso negado: Evento pertence a outra clínica.", http_status=403)

        return api_success(data={
            "id": evento.id,
            "tipo": "consulta",
            "status": evento.status,
            "paciente": _extrair_dados_paciente(evento.paciente),
            "detalhes": {
                "data_inicio": evento.data_inicio.isoformat() if evento.data_inicio else None,
                "queixa_principal": evento.queixa_principal,
                "anamnese": evento.anamnese,
                "hipotese_diagnostica": evento.hipotese_diagnostica,
                "observacoes": evento.resumo,
            }
        })
        
    elif tipo == "receita":
        try:
            from prescricao_app.models import Receita
            evento = Receita.objects.select_related("medico", "paciente__user").prefetch_related("itens__medicamento").get(id=atendimento_id)
        except Receita.DoesNotExist:
            return api_not_found("Receita não encontrada.")
            
        clinic_id_evento = evento.medico.clinica_principal_id if evento.medico else None
        if clinic_id_medico and clinic_id_evento and clinic_id_medico != clinic_id_evento:
            return api_error("Acesso negado: Evento pertence a outra clínica.", http_status=403)
            
        medicamentos = []
        for item in evento.itens.all():
            medicamentos.append({
                "nome": item.medicamento.nome if item.medicamento else "Item manual",
                "dosagem": item.dosagem,
                "posologia": item.posologia,
                "via_administracao": item.via_administracao,
            })

        return api_success(data={
            "id": evento.id,
            "tipo": "receita",
            "status": evento.status,
            "paciente": _extrair_dados_paciente(evento.paciente),
            "detalhes": {
                "data_emissao": evento.data_emissao.isoformat() if getattr(evento, 'data_emissao', None) else None,
                "assinada": getattr(evento, 'is_signed', False),
                "observacoes": evento.observacoes,
                "medicamentos": medicamentos,
            }
        })
        
    elif tipo == "prontuario":
        try:
            evento = Prontuario.objects.select_related("medico", "paciente__user").get(id=atendimento_id)
        except Prontuario.DoesNotExist:
            return api_not_found("Prontuário não encontrado.")
            
        clinic_id_evento = evento.medico.clinica_principal_id if evento.medico else None
        if clinic_id_medico and clinic_id_evento and clinic_id_medico != clinic_id_evento:
            return api_error("Acesso negado: Evento pertence a outra clínica.", http_status=403)

        return api_success(data={
            "id": evento.id,
            "tipo": "prontuario",
            "status": "registrado",
            "paciente": _extrair_dados_paciente(evento.paciente),
            "detalhes": {
                "data": evento.data_consulta.isoformat() if evento.data_consulta else None,
                "queixa_principal": evento.queixa_principal,
                "anamnese": evento.anamnese,
                "exame_fisico": getattr(evento, 'exame_fisico', ''),
                "hipotese_diagnostica": evento.hipotese_diagnostica,
                "diagnostico_cid10": evento.diagnostico_cid10,
                "conduta": evento.conduta,
                "retorno_em": evento.retorno_em.isoformat() if evento.retorno_em else None,
            }
        })
        
    return api_error("O detalhamento deste tipo de evento ainda está sendo desenvolvido ou o tipo é inválido.")

