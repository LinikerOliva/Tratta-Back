"""
trathea_core/audit/middleware.py
Middleware de auditoria automática para operações de escrita.
"""
import logging

logger = logging.getLogger("trathea")

# Métodos que modificam dados
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths que NÃO devem gerar log automático (já têm log manual)
EXCLUDED_PATHS = {
    "/api/auth/login/",
    "/api/auth/logout/",
    "/api/receitas/",          # log manual (mais detalhado)
    "/api/prontuarios/",       # log manual
    "/api/solicitacoes/",      # log manual
}


class AuditMiddleware:
    """
    Middleware que loga automaticamente operações de escrita não mapeadas.
    Operações críticas (assinatura, prontuário) têm log manual mais detalhado.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.method in WRITE_METHODS
            and request.path not in EXCLUDED_PATHS
            and hasattr(request, "user")
            and request.user.is_authenticated
            and 200 <= response.status_code < 300
        ):
            self._log_generic_write(request, response)

        return response

    def _log_generic_write(self, request, response):
        """Log genérico para escritas não cobertas pelos logs manuais."""
        try:
            logger.info(
                f"[AUDIT] {request.method} {request.path} "
                f"user={request.user.email} status={response.status_code}"
            )
        except Exception as e:
            logger.error(f"AuditMiddleware error: {e}")
