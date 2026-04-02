"""
paciente_app/views_settings.py
Views de Configurações do Paciente.

Endpoints:
    GET/PATCH  /api/patients/me/health-data/  — Dados de saúde (sensíveis)
    GET/PATCH  /api/patients/me/preferences/  — Preferências de notificação
"""
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error
from trathea_core.audit.audit import log_audit
from trathea_core.audit.models import LogAuditoria

from paciente_app.models import Paciente

logger = logging.getLogger("trathea")


def _get_paciente(user):
    try:
        return user.paciente
    except Exception:
        return None


# ── Dados de Saúde ────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Paciente"],
    summary="Dados de saúde do paciente (sensíveis — LGPD Artigo 11)",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def paciente_health_data_view(request):
    """
    GET  /api/patients/me/health-data/
    PATCH /api/patients/me/health-data/
    """
    paciente = _get_paciente(request.user)
    if not paciente:
        return api_error("Perfil de paciente não encontrado.", http_status=404)

    if request.method == "GET":
        data = {
            "tipo_sanguineo": paciente.tipo_sanguineo,
            "alergias": paciente.alergias,
            "doencas_cronicas": paciente.doencas_cronicas,
            "medicamentos_uso_continuo": paciente.medicamentos_uso_continuo,
            "convenio_nome": paciente.convenio_nome,
            "convenio_numero": paciente.convenio_numero,
            "data_nascimento": paciente.data_nascimento,
        }
        return api_success(data=data)

    # PATCH — campos de saúde (sensíveis)
    campos_saude = {
        "tipo_sanguineo", "alergias", "doencas_cronicas", "medicamentos_uso_continuo",
        "convenio_nome", "convenio_numero", "data_nascimento"
    }

    updated = {}
    for field in campos_saude:
        if field in request.data:
            setattr(paciente, field, request.data[field])
            updated[field] = request.data[field]

    if updated:
        paciente.save(update_fields=list(updated.keys()))
        log_audit(
            request,
            LogAuditoria.Acao.ATUALIZAR,
            modelo="Paciente",
            pk_objeto=str(paciente.pk),
            detalhes={"campos_saude_atualizados": list(updated.keys())},
        )

    return api_success(message="Dados de saúde atualizados.", data={"updated": list(updated.keys())})


# ── Preferências de Notificação ───────────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Paciente"],
    summary="Preferências de notificação do paciente",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def paciente_preferences_view(request):
    """
    GET  /api/patients/me/preferences/
    PATCH /api/patients/me/preferences/
    """
    paciente = _get_paciente(request.user)
    if not paciente:
        return api_error("Perfil do paciente não encontrado.", http_status=404)

    if request.method == "GET":
        data = {
            "notificacoes_whatsapp": paciente.notificacoes_whatsapp,
            "notificacoes_email": paciente.notificacoes_email,
        }
        return api_success(data=data)

    # PATCH — salva preferências
    campos = ["notificacoes_whatsapp", "notificacoes_email"]
    updated = []
    
    for field in campos:
        if field in request.data:
            val = str(request.data[field]).lower() in ("true", "1", "yes")
            setattr(paciente, field, val)
            updated.append(field)

    if updated:
        paciente.save(update_fields=updated)

    return api_success(message="Preferências salvas.", data={"updated": updated})
