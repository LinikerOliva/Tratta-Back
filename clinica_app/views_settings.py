"""
clinica_app/views_settings.py
Views de Configurações da Clínica e Admin.

Endpoints:
    GET/PATCH  /api/clinics/me/settings/   — Dados da clínica (razão social, CNPJ, logo)
    GET/PATCH  /api/clinics/me/triagem/    — Protocolo de Manchester on/off
    GET        /api/clinics/me/rbac/       — Listar usuários da clínica com permissões
    PATCH      /api/clinics/me/rbac/       — Alterar permissões de um membro
"""
import logging

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error
from trathea_core.audit.audit import log_audit
from trathea_core.audit.models import LogAuditoria

from clinica_app.models import Clinica, Secretaria
from core_app.models import CustomUser

logger = logging.getLogger("trathea")


def _get_clinica(user):
    try:
        return user.clinica
    except Exception:
        return None


# ── Configurações da Clínica ──────────────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Clínica"],
    summary="Configurações da clínica autenticada",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def clinica_settings_view(request):
    """
    GET  /api/clinics/me/settings/
    PATCH /api/clinics/me/settings/
    """
    clinica = _get_clinica(request.user)
    if not clinica:
        return api_error("Perfil de clínica não encontrado.", http_status=404)

    if request.method == "GET":
        data = {
            "nome_fantasia": clinica.nome_fantasia,
            "razao_social": clinica.razao_social,
            "cnpj": clinica.cnpj,
            "telefone": clinica.telefone,
            "email_contato": clinica.email_contato,
            "endereco": clinica.endereco,
            "horario_funcionamento": clinica.horario_funcionamento,
            "logo_url": (
                request.build_absolute_uri(clinica.logo.url)
                if clinica.logo else None
            ),
            "ativa": clinica.ativa,
        }
        return api_success(data=data)

    # PATCH
    CAMPOS_CRITICOS = {"cnpj", "razao_social"}
    campos_alterados = {}

    mutable_fields = {
        "nome_fantasia", "razao_social", "cnpj", "telefone",
        "email_contato", "endereco", "horario_funcionamento"
    }

    updated = {}
    for field in mutable_fields:
        if field in request.data:
            if field in CAMPOS_CRITICOS:
                campos_alterados[field] = {
                    "antes": getattr(clinica, field),
                    "depois": request.data[field],
                }
            setattr(clinica, field, request.data[field])
            updated[field] = request.data[field]

    if "logo" in request.FILES:
        clinica.logo = request.FILES["logo"]
        updated["logo"] = True

    if updated:
        clinica.save()

        if campos_alterados:
            log_audit(
                request,
                LogAuditoria.Acao.ALTERAR_DADOS_CRITICOS,
                modelo="Clinica",
                pk_objeto=str(clinica.pk),
                dados_extra=campos_alterados,
            )
        else:
            log_audit(request, LogAuditoria.Acao.ATUALIZAR, modelo="Clinica", pk_objeto=str(clinica.pk))

    return api_success(
        message="Configurações da clínica atualizadas.",
        data={"updated": list(updated.keys())},
    )


# ── Triagem (Protocolo de Manchester) ────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Clínica"],
    summary="Ativar/Desativar Protocolo de Manchester na triagem",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def clinica_triagem_view(request):
    """
    GET  /api/clinics/me/triagem/
    PATCH /api/clinics/me/triagem/  → body: { "manchester_ativo": true/false }
    """
    clinica = _get_clinica(request.user)
    if not clinica:
        return api_error("Perfil de clínica não encontrado.", http_status=404)

    if request.method == "GET":
        data = {
            "manchester_ativo": getattr(clinica, "manchester_ativo", False),
        }
        return api_success(data=data)

    val = str(request.data.get("manchester_ativo", "false")).lower() in ("true", "1", "yes")
    try:
        clinica.manchester_ativo = val
        clinica.save(update_fields=["manchester_ativo"])
    except Exception:
        # Campo ainda não migrado — salva tudo
        clinica.save()

    log_audit(
        request,
        LogAuditoria.Acao.ATUALIZAR,
        modelo="Clinica",
        pk_objeto=str(clinica.pk),
        dados_extra={"manchester_ativo": val},
    )

    return api_success(message=f"Protocolo de Manchester {'ativado' if val else 'desativado'}.")


# ── RBAC — Gestão de membros ──────────────────────────────────────────────────
@extend_schema(
    tags=["Configurações — Clínica"],
    summary="RBAC: listar e atualizar permissões dos membros da clínica",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def clinica_rbac_view(request):
    """
    GET   /api/clinics/me/rbac/                 — lista secretarias/médicos
    PATCH /api/clinics/me/rbac/                 — atualiza permissão de um membro
          body: { "secretaria_id": <id>, "pode_agendar": bool, "pode_ver_prontuario": bool }
    """
    clinica = _get_clinica(request.user)
    if not clinica:
        return api_error("Perfil de clínica não encontrado.", http_status=404)

    if request.method == "GET":
        secretarias = list(
            clinica.secretarias.select_related("user").values(
                "id",
                "user__nome_completo",
                "user__email",
                "cargo",
                "pode_agendar",
                "pode_ver_prontuario",
            )
        )
        medicos = list(
            clinica.medicos.select_related("user").values(
                "id",
                "user__nome_completo",
                "user__email",
                "especialidade",
                "crm",
            )
        )
        return api_success(data={"secretarias": secretarias, "medicos": medicos})

    # PATCH — altera permissões de uma secretaria
    sec_id = request.data.get("secretaria_id")
    if not sec_id:
        return api_error("secretaria_id é obrigatório.")

    try:
        sec = Secretaria.objects.get(id=sec_id, clinica=clinica)
    except Secretaria.DoesNotExist:
        return api_error("Membro não encontrado.", http_status=404)

    campos = {}
    if "pode_agendar" in request.data:
        sec.pode_agendar = str(request.data["pode_agendar"]).lower() in ("true", "1")
        campos["pode_agendar"] = sec.pode_agendar
    if "pode_ver_prontuario" in request.data:
        sec.pode_ver_prontuario = str(request.data["pode_ver_prontuario"]).lower() in ("true", "1")
        campos["pode_ver_prontuario"] = sec.pode_ver_prontuario
    if "cargo" in request.data:
        sec.cargo = request.data["cargo"]
        campos["cargo"] = sec.cargo

    sec.save()
    log_audit(
        request,
        LogAuditoria.Acao.ATUALIZAR,
        modelo="Secretaria",
        pk_objeto=str(sec.pk),
        dados_extra=campos,
    )

    return api_success(message="Permissões atualizadas.", data=campos)
