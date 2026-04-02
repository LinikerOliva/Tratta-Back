"""
trathea_core/utils/exceptions.py
Handler global de exceções — converte QUALQUER erro para o padrão
{"success": false, "data": null, "message": "...", "errors": [...]}
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
    NotFound,
    Throttled,
)
from rest_framework import status

logger = logging.getLogger("trathea")


def custom_exception_handler(exc, context):
    """
    Handler de exceção personalizado para o DRF.
    Mapeia todos os tipos de exception para o formato padronizado Trathea.
    """
    response = exception_handler(exc, context)

    if response is not None:
        message, errors = _extract_message_and_errors(exc, response)
        response.data = {
            "success": False,
            "data": None,
            "message": message,
            "errors": errors,
        }

    return response


def _extract_message_and_errors(exc, response) -> tuple[str, list | dict]:
    """Extrai mensagem legível e erros detalhados da exception."""
    if isinstance(exc, ValidationError):
        return "Dados inválidos. Verifique os campos e tente novamente.", response.data

    if isinstance(exc, NotAuthenticated):
        return "Autenticação necessária. Faça login para continuar.", []

    if isinstance(exc, AuthenticationFailed):
        return "Credenciais inválidas ou token expirado.", []

    if isinstance(exc, PermissionDenied):
        return "Acesso negado. Você não tem permissão para esta operação.", []

    if isinstance(exc, NotFound):
        return "Recurso não encontrado.", []

    if isinstance(exc, Throttled):
        wait = getattr(exc, "wait", None)
        msg = "Muitas requisições. " + (f"Tente novamente em {int(wait)} segundos." if wait else "Tente mais tarde.")
        return msg, []

    # Fallback genérico
    logger.error(f"Exceção não mapeada: {type(exc).__name__}: {exc}", exc_info=True)
    return "Ocorreu um erro inesperado.", []
