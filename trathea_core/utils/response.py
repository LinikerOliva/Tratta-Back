"""
trathea_core/utils/response.py
Padrão único de resposta para toda a API Trathea.

Formato:
{
    "success": bool,
    "data": {} | [] | null,
    "message": "string",
    "errors": []
}
"""
from typing import Any, Optional, Union
from rest_framework.response import Response
from rest_framework import status


def api_success(
    data: Any = None,
    message: str = "Operação realizada com sucesso.",
    http_status: int = status.HTTP_200_OK,
) -> Response:
    """
    Retorna uma resposta de sucesso padronizada.

    Args:
        data: Payload principal da resposta.
        message: Mensagem descritiva.
        http_status: Código HTTP (padrão 200).

    Returns:
        Response DRF formatada.
    """
    return Response(
        {
            "success": True,
            "data": data,
            "message": message,
            "errors": [],
        },
        status=http_status,
    )


def api_created(
    data: Any = None,
    message: str = "Recurso criado com sucesso.",
) -> Response:
    """Atalho para respostas 201 Created."""
    return api_success(data=data, message=message, http_status=status.HTTP_201_CREATED)


def api_error(
    message: str = "Ocorreu um erro.",
    errors: Optional[Union[dict, list]] = None,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """
    Retorna uma resposta de erro padronizada.

    Args:
        message: Mensagem de erro legível para o usuário.
        errors: Dict ou lista de erros detalhados (campo: [msgs]).
        http_status: Código HTTP (padrão 400).

    Returns:
        Response DRF formatada.
    """
    return Response(
        {
            "success": False,
            "data": None,
            "message": message,
            "errors": errors or [],
        },
        status=http_status,
    )


def api_not_found(message: str = "Recurso não encontrado.") -> Response:
    """Atalho para 404 Not Found."""
    return api_error(message=message, http_status=status.HTTP_404_NOT_FOUND)


def api_forbidden(message: str = "Acesso negado. Permissão insuficiente.") -> Response:
    """Atalho para 403 Forbidden."""
    return api_error(message=message, http_status=status.HTTP_403_FORBIDDEN)


def api_unauthorized(message: str = "Autenticação necessária.") -> Response:
    """Atalho para 401 Unauthorized."""
    return api_error(message=message, http_status=status.HTTP_401_UNAUTHORIZED)


def api_server_error(message: str = "Erro interno do servidor. Contate o suporte.") -> Response:
    """Atalho para 500 Internal Server Error."""
    return api_error(message=message, http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def api_service_unavailable(message: str = "Serviço temporariamente indisponível.") -> Response:
    """Atalho para 503 — Gov.br offline, por exemplo."""
    return api_error(message=message, http_status=status.HTTP_503_SERVICE_UNAVAILABLE)
