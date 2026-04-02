"""
medico_app/views_settings.py
Views de Configurações do Médico.

Endpoints:
    GET/PATCH  /api/doctors/me/settings/    — Dados profissionais, agenda, bio
    GET/PATCH  /api/doctors/me/receituario/ — Configuração do receituário (logo, cabeçalho, fonte)
"""
import logging

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error
from trathea_core.audit.models import LogAuditoria

from medico_app.models import Medico, Disponibilidade, ReceituarioConfig

logger = logging.getLogger("trathea")


def _get_medico(user):
    """Retorna o perfil Medico do usuário ou None."""
    try:
        return user.medico
    except Medico.DoesNotExist:
        return None


# ── Configurações profissionais ───────────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Médico"],
    summary="Configurações profissionais do médico autenticado",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def medico_settings_view(request):
    """
    GET  /api/doctors/me/settings/
    PATCH /api/doctors/me/settings/
    """
    medico = _get_medico(request.user)
    if not medico:
        return api_error("Perfil de médico não encontrado.", http_status=404)

    if request.method == "GET":
        disponibilidades = list(
            medico.disponibilidades.filter(ativo=True).values(
                "id", "dia_semana", "hora_inicio", "hora_fim", "duracao_consulta_min", "ativo"
            )
        )
        data = {
            "crm": medico.crm,
            "crm_estado": medico.crm_estado,
            "rqe": medico.rqe,
            "especialidade": medico.especialidade,
            "sub_especialidades": medico.sub_especialidades,
            "bio": medico.bio,
            "atende_convenio": medico.atende_convenio,
            "is_govbr_linked": medico.is_govbr_linked,
            "disponibilidades": disponibilidades,
        }
        return api_success(data=data)

    # PATCH — atualiza campos permitidos
    CAMPOS_CRITICOS = {"crm", "crm_estado", "rqe"}
    campos_alterados = {}

    mutable_fields = {
        "especialidade", "sub_especialidades", "bio", "atende_convenio"
    }
    # CRM e RQE só podem ser alterado com log de auditoria extra
    if "crm" in request.data or "crm_estado" in request.data or "rqe" in request.data:
        mutable_fields.update({"crm", "crm_estado", "rqe"})
        campos_alterados["campo_critico"] = "CRM ou RQE alterado"

    updated = {}
    for field in mutable_fields:
        if field in request.data:
            val = request.data[field]
            if field == "atende_convenio":
                val = str(val).lower() in ("true", "1", "yes")
            setattr(medico, field, val)
            updated[field] = val

    if updated:
        medico.save(update_fields=list(updated.keys()))

        if campos_alterados:
            log_audit(
                request,
                LogAuditoria.Acao.ALTERAR_DADOS_CRITICOS,
                modelo="Medico",
                pk_objeto=str(medico.id),
                dados_extra=campos_alterados,
            )
        else:
            log_audit(request, LogAuditoria.Acao.ATUALIZAR, modelo="Medico", pk_objeto=str(medico.id))

    return api_success(message="Configurações profissionais atualizadas.", data={"updated": list(updated.keys())})


# ── Configuração do Receituário ───────────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Médico"],
    summary="Configuração do receituário médico (cabeçalho, logo, fonte)",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def medico_receituario_view(request):
    """
    GET  /api/doctors/me/receituario/
    PATCH /api/doctors/me/receituario/
    """
    medico = _get_medico(request.user)
    if not medico:
        return api_error("Perfil de médico não encontrado.", http_status=404)

    # Usa a clínica principal para logo (se vinculado)
    clinica = medico.clinica_principal

    if request.method == "GET":
        # Tenta ler configuração de receituário
        config, created = ReceituarioConfig.objects.get_or_create(medico=medico)
        data = {
            "cabecalho": config.cabecalho or f"Dr(a). {medico.user.nome_completo}",
            "rodape": config.rodape,
            "fonte_nome": config.fonte_nome,
            "margem_superior": config.margem_superior,
            "margem_inferior": config.margem_inferior,
            "margem_esquerda": config.margem_esquerda,
            "margem_direita": config.margem_direita,
            "logotipo_clinica": request.build_absolute_uri(config.logotipo_clinica.url) if config.logotipo_clinica else None,
            "crm_display": f"CRM/{medico.crm_estado} {medico.crm}",
            "especialidade": medico.especialidade,
        }
        return api_success(data=data)

    # PATCH — salva no modelo ReceituarioConfig
    config, created = ReceituarioConfig.objects.get_or_create(medico=medico)
    campos = [
        "cabecalho", "rodape", "fonte_nome",
        "margem_superior", "margem_inferior", "margem_esquerda", "margem_direita"
    ]
    updated = []
    
    for field in campos:
        if field in request.data:
            val = request.data[field]
            if "margem" in field:
                val = int(val)
            setattr(config, field, val)
            updated.append(field)
            
    if "logotipo_clinica" in request.FILES:
        config.logotipo_clinica = request.FILES["logotipo_clinica"]
        updated.append("logotipo_clinica")
        
    if updated:
        config.save()
        log_audit(request, LogAuditoria.Acao.ATUALIZAR, modelo="ReceituarioConfig", pk_objeto=str(config.pk))

    return api_success(message="Configurações do receituário salvas.", data={"updated": updated})


# ── Agenda (disponibilidades) ─────────────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Médico"],
    summary="Gerenciar disponibilidade de agenda do médico",
)
@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def medico_agenda_view(request):
    """
    GET    /api/doctors/me/agenda/           — listar disponibilidades
    POST   /api/doctors/me/agenda/           — criar slot
    DELETE /api/doctors/me/agenda/?id=<pk>  — remover slot
    """
    medico = _get_medico(request.user)
    if not medico:
        return api_error("Perfil de médico não encontrado.", http_status=404)

    if request.method == "GET":
        slots = list(
            medico.disponibilidades.values(
                "id", "dia_semana", "hora_inicio", "hora_fim", "duracao_consulta_min", "ativo"
            )
        )
        return api_success(data=slots)

    if request.method == "POST":
        try:
            slot = Disponibilidade.objects.create(
                medico=medico,
                dia_semana=int(request.data["dia_semana"]),
                hora_inicio=request.data["hora_inicio"],
                hora_fim=request.data["hora_fim"],
                duracao_consulta_min=int(request.data.get("duracao_consulta_min", 30)),
            )
            return api_success(
                data={"id": slot.id, "dia_semana": slot.dia_semana},
                message="Horário adicionado.",
            )
        except Exception as e:
            return api_error(f"Erro ao criar horário: {e}")

    if request.method == "DELETE":
        slot_id = request.GET.get("id")
        try:
            Disponibilidade.objects.filter(medico=medico, id=slot_id).delete()
            return api_success(message="Horário removido.")
        except Exception as e:
            return api_error(f"Erro ao remover horário: {e}")
