"""
core_app/views/password_reset.py
Views de recuperação de senha — solicitar reset e confirmar nova senha.

Fluxo:
  1. POST /api/auth/reset-password/         → recebe { email }, gera token, "envia" link
  2. POST /api/auth/reset-password/confirm/  → recebe { uid, token, new_password }, reseta
"""
import logging

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle

from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error
from trathea_core.audit.audit import log_audit
from trathea_core.audit.models import LogAuditoria

from core_app.models import CustomUser

logger = logging.getLogger("trathea")


# ── Solicitar Reset ──────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Solicitar redefinição de senha",
    description="Envia um link de redefinição para o e-mail cadastrado.",
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def reset_password_request_view(request):
    """
    POST /api/auth/reset-password/

    Body: { "email": "usuario@example.com" }

    Sempre retorna sucesso (200) para evitar enumeração de e-mails.
    """
    email = (request.data.get("email") or "").strip().lower()

    if not email:
        return api_error(
            message="Informe o e-mail cadastrado.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    # Resposta genérica — NUNCA dizer se o e-mail existe ou não (segurança)
    success_msg = "Se o e-mail estiver cadastrado, você receberá as instruções para redefinir sua senha."

    try:
        user = CustomUser.objects.get(email=email, is_active=True)
    except CustomUser.DoesNotExist:
        # Log silencioso, retorna mesmo assim
        logger.info(f"Password reset solicitado para e-mail não encontrado: {email}")
        return api_success(message=success_msg)

    # Gera token seguro usando o token generator do Django
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Monta URL de reset (aponta para o front-end public app)
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    reset_link = f"{frontend_url}/reset-password?uid={uid}&token={token}"

    # Envia e-mail (em dev vai para console)
    try:
        send_mail(
            subject="🔑 Tratta — Redefinição de Senha",
            message=(
                f"Olá, {user.nome_completo}!\n\n"
                f"Recebemos uma solicitação para redefinir sua senha na Tratta.\n\n"
                f"Clique no link abaixo para criar uma nova senha:\n"
                f"{reset_link}\n\n"
                f"Este link expira em 1 hora.\n\n"
                f"Se você não solicitou, ignore este e-mail.\n\n"
                f"— Equipe Tratta"
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tratta.io'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email} | uid={uid}")
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail de reset: {e}", exc_info=True)
        # Mesmo com erro de envio, não revela ao usuário

    log_audit(
        request,
        LogAuditoria.Acao.ALTERAR_SENHA,
        modelo="CustomUser",
        pk_objeto=str(user.pk),
        detalhes={"acao": "reset_password_request", "email": email},
    )

    return api_success(
        data={"uid": uid, "token": token},  # ← Útil em dev (remover em prod)
        message=success_msg,
    )


# ── Confirmar Reset ──────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Confirmar redefinição de senha",
    description="Valida o token e define a nova senha.",
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def reset_password_confirm_view(request):
    """
    POST /api/auth/reset-password/confirm/

    Body: { "uid": "...", "token": "...", "new_password": "...", "confirm_password": "..." }
    """
    uid = request.data.get("uid", "")
    token = request.data.get("token", "")
    new_password = request.data.get("new_password", "")
    confirm_password = request.data.get("confirm_password", "")

    # Validações
    if not uid or not token:
        return api_error(
            message="Link inválido ou expirado.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    if not new_password:
        return api_error(
            message="Informe a nova senha.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    if len(new_password) < 8:
        return api_error(
            message="A senha deve ter no mínimo 8 caracteres.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    if new_password != confirm_password:
        return api_error(
            message="As senhas não coincidem.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    # Decodifica UID
    try:
        user_pk = force_str(urlsafe_base64_decode(uid))
        user = CustomUser.objects.get(pk=user_pk, is_active=True)
    except (CustomUser.DoesNotExist, ValueError, OverflowError, TypeError):
        return api_error(
            message="Link inválido ou expirado.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    # Valida token
    if not default_token_generator.check_token(user, token):
        return api_error(
            message="Link expirado. Solicite uma nova redefinição de senha.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    # Redefine a senha
    user.set_password(new_password)
    user.save(update_fields=["password"])

    log_audit(
        request,
        LogAuditoria.Acao.ALTERAR_SENHA,
        modelo="CustomUser",
        pk_objeto=str(user.pk),
        detalhes={"acao": "reset_password_confirm"},
    )

    logger.info(f"Password reset completed for {user.email}")

    return api_success(message="Senha redefinida com sucesso! Faça login com a nova senha.")
