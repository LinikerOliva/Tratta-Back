"""
core_app/views/settings.py
Views de Configurações de Perfil — Comum a todos os usuários.

Endpoints:
    GET/PATCH  /api/users/me/profile/    — Dados básicos + foto
    GET        /api/users/me/access-log/ — Últimos acessos (simulado via LogAuditoria)
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error
from trathea_core.audit.audit import log_audit
from trathea_core.audit.models import LogAuditoria

from core_app.models import UserProfile
from core_app.serializers import CustomUserSerializer, UserProfileSerializer

logger = logging.getLogger("trathea")


# ── Perfil do usuário (dados básicos) ────────────────────────────────────────
@extend_schema(
    tags=["Configurações"],
    summary="Obter ou atualizar perfil do usuário autenticado",
    description="Retorna/atualiza dados básicos (nome, telefone, foto, etc.).",
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def my_profile_view(request):
    """
    GET  /api/users/me/profile/  → retorna user + perfil
    PATCH /api/users/me/profile/ → atualiza dados básicos (multipart para foto)
    """
    user = request.user

    if request.method == "GET":
        return api_success(data=CustomUserSerializer(user).data)

    # PATCH — atualiza nome no CustomUser
    user_fields = {}
    if "nome_completo" in request.data:
        user_fields["nome_completo"] = request.data["nome_completo"]

    if user_fields:
        for field, value in user_fields.items():
            setattr(user, field, value)
        user.save(update_fields=list(user_fields.keys()))

    # Atualiza / cria UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile_data = {
        k: v for k, v in request.data.items()
        if k not in ("nome_completo",)
    }
    # Foto
    if "foto" in request.FILES:
        profile.foto = request.FILES["foto"]

    profile_serializer = UserProfileSerializer(
        profile, data=profile_data, partial=True, context={"request": request}
    )
    if not profile_serializer.is_valid():
        return api_error(
            message="Dados de perfil inválidos.",
            errors=profile_serializer.errors,
        )
    profile_serializer.save()

    log_audit(request, LogAuditoria.Acao.ATUALIZAR, modelo="UserProfile", pk_objeto=str(user.id))

    return api_success(
        data=CustomUserSerializer(user).data,
        message="Perfil atualizado com sucesso.",
    )


# ── Log de Acessos ────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Configurações"],
    summary="Últimos acessos do usuário (IP e dispositivo)",
    description="Retorna os últimos 20 registros de login do usuário autenticado.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_access_log_view(request):
    """GET /api/users/me/access-log/"""
    logs = (
        LogAuditoria.objects.filter(
            usuario=request.user,
            acao=LogAuditoria.Acao.LOGIN,
        )
        .order_by("-timestamp")
        [:20]
    )

    data = [
        {
            "timestamp": log.timestamp,
            "ip": log.ip_address or "—",
            "user_agent": log.detalhes.get("user_agent", "—") if log.detalhes else "—",
        }
        for log in logs
    ]

    return api_success(data=data)


# ── Segurança (Change Password and 2FA) ───────────────────────────────────────
@extend_schema(
    tags=["Configurações"],
    summary="Configurações de segurança: alterar senha e 2FA",
    description="Atualizar senha ou habilitar/desabilitar autenticação em duas etapas.",
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def user_security_view(request):
    """
    PATCH /api/users/me/security/
    Body for 2FA: {"is_2fa_enabled": true/false}
    Body for password: {"old_password": "...", "new_password": "..."}
    """
    user = request.user
    updated = []

    # Password Change
    if "new_password" in request.data and "old_password" in request.data:
        if not user.check_password(request.data["old_password"]):
            return api_error("Senha atual incorreta.", http_status=400)
        
        user.set_password(request.data["new_password"])
        user.save()
        updated.append("password")
        log_audit(request, LogAuditoria.Acao.ALTERAR_DADOS_CRITICOS, modelo="CustomUser", pk_objeto=str(user.id), detalhes={"campo": "password"})

    # 2FA Toggle
    if "is_2fa_enabled" in request.data:
        val = str(request.data["is_2fa_enabled"]).lower() in ("true", "1", "yes")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.is_2fa_enabled = val
        profile.save(update_fields=["is_2fa_enabled"])
        updated.append("is_2fa_enabled")
        log_audit(request, LogAuditoria.Acao.ATUALIZAR, modelo="UserProfile", pk_objeto=str(user.id), detalhes={"is_2fa_enabled": val})

    if not updated:
        return api_error("Nenhum dado válido para atualizar. Envie 'old_password/new_password' ou 'is_2fa_enabled'.")

    return api_success(message="Configurações de segurança atualizadas.", data={"updated": updated})
