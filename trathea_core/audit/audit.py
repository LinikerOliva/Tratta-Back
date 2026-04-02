"""
trathea_core/audit/audit.py
Função centralizada de auditoria.

Uso:
    from trathea_core.audit.audit import log_audit
    from trathea_core.audit.models import LogAuditoria

    log_audit(
        request=request,
        acao=LogAuditoria.Acao.ASSINAR_RECEITA,
        modelo="Receita",
        pk_objeto=str(receita.id),
        dados_extra={"hash": receita.hash_verificacao},
    )
"""
import logging
from typing import Optional, Any
from django.db import transaction

logger = logging.getLogger("trathea")


def log_audit(
    request,
    acao: str,
    modelo: str = "",
    pk_objeto: str = "",
    dados_extra: Optional[dict] = None,
) -> None:
    """
    Registra uma entrada de auditoria de forma assíncrona (não bloqueante).

    Args:
        request: Request DRF com user e META.
        acao: Constante de LogAuditoria.Acao.
        modelo: Nome do modelo afetado (ex: 'Receita').
        pk_objeto: ID do objeto afetado.
        dados_extra: Dados adicionais (diff, hash, etc).
    """
    from trathea_core.audit.models import LogAuditoria  # import local para evitar circular

    try:
        usuario = request.user if request.user.is_authenticated else None
        ip = _get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

        # Usa transaction.on_commit para garantir que o log seja salvo
        # após o commit da transação principal
        def _save_log():
            LogAuditoria.objects.create(
                usuario=usuario,
                acao=acao,
                modelo=modelo,
                pk_objeto=str(pk_objeto),
                ip_address=ip,
                user_agent=user_agent,
                dados_extra=dados_extra,
            )

        transaction.on_commit(_save_log)

    except Exception as e:
        # Auditoria NUNCA deve quebrar o fluxo principal
        logger.error(f"Falha ao registrar auditoria [{acao}]: {e}", exc_info=True)


def _get_client_ip(request) -> Optional[str]:
    """Extrai o IP real do cliente mesmo via proxy/load balancer."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
