"""
tests/trathea_core/test_response.py
Testes das funções utilitárias de resposta padronizada.
"""
import pytest
from rest_framework import status

from trathea_core.utils.response import (
    api_success,
    api_created,
    api_error,
    api_not_found,
    api_forbidden,
    api_unauthorized,
    api_server_error,
    api_service_unavailable,
)


class TestApiSuccess:
    def test_resposta_padrao(self):
        response = api_success(data={"id": 1})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"] == {"id": 1}
        assert response.data["errors"] == []

    def test_com_mensagem_customizada(self):
        response = api_success(message="Operação OK")
        assert response.data["message"] == "Operação OK"

    def test_com_status_customizado(self):
        response = api_success(http_status=status.HTTP_202_ACCEPTED)
        assert response.status_code == status.HTTP_202_ACCEPTED


class TestApiCreated:
    def test_retorna_201(self):
        response = api_created(data={"id": 1})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True


class TestApiError:
    def test_erro_padrao_400(self):
        response = api_error(message="Campo inválido")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False
        assert response.data["message"] == "Campo inválido"

    def test_com_erros_detalhados(self):
        errors = {"email": ["Este campo é obrigatório."]}
        response = api_error(errors=errors)
        assert response.data["errors"] == errors


class TestApiNotFound:
    def test_retorna_404(self):
        response = api_not_found("Paciente não encontrado.")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["success"] is False


class TestApiForbidden:
    def test_retorna_403(self):
        response = api_forbidden()
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestApiUnauthorized:
    def test_retorna_401(self):
        response = api_unauthorized()
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestApiServerError:
    def test_retorna_500(self):
        response = api_server_error()
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestApiServiceUnavailable:
    def test_retorna_503(self):
        response = api_service_unavailable()
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
