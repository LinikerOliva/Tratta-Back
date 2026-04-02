"""
tests/core_app/test_auth.py
Testes unitários para autenticação do core_app.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def usuario_medico(db):
    """Cria um usuário médico de teste."""
    from core_app.models import CustomUser, UserProfile

    user = CustomUser.objects.create_user(
        email="drteste@trathea.app",
        password="Senha@Segura123",
        nome_completo="Dr. Teste Silva",
        role="medico",
    )
    UserProfile.objects.create(user=user, cpf="98765432100")
    return user


@pytest.mark.django_db
class TestLogin:
    """Testes do endpoint POST /api/auth/login/"""

    def test_login_com_credenciais_validas(self, client, usuario_medico):
        url = reverse("auth-login")
        response = client.post(url, {
            "email": "drteste@trathea.app",
            "password": "Senha@Segura123",
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]
        assert response.data["data"]["user"]["role"] == "medico"

    def test_login_com_senha_errada(self, client, usuario_medico):
        url = reverse("auth-login")
        response = client.post(url, {
            "email": "drteste@trathea.app",
            "password": "SenhaErrada",
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["success"] is False

    def test_login_com_email_inexistente(self, client):
        url = reverse("auth-login")
        response = client.post(url, {
            "email": "naoexiste@trathea.app",
            "password": "qualquercoisa",
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["success"] is False


@pytest.mark.django_db
class TestRegister:
    """Testes do endpoint POST /api/auth/register/"""

    def test_registro_valido_medico(self, client):
        url = reverse("auth-register")
        response = client.post(url, {
            "email": "nuevo@trathea.app",
            "nome_completo": "Dra. Nova Silva",
            "role": "medico",
            "password": "Senha@Segura123",
            "password_confirm": "Senha@Segura123",
            "cpf": "98765432100",
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True

    def test_registro_com_senhas_diferentes(self, client):
        url = reverse("auth-register")
        response = client.post(url, {
            "email": "test@trathea.app",
            "nome_completo": "Teste",
            "role": "paciente",
            "password": "Senha@Segura123",
            "password_confirm": "SenhaDiferente",
            "cpf": "12345678909",
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_registro_com_cpf_invalido(self, client):
        url = reverse("auth-register")
        response = client.post(url, {
            "email": "test@trathea.app",
            "nome_completo": "Teste",
            "role": "paciente",
            "password": "Senha@Segura123",
            "password_confirm": "Senha@Segura123",
            "cpf": "00000000000",  # CPF inválido
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRBAC:
    """Testes de isolamento de perfis RBAC."""

    def test_paciente_nao_acessa_rota_de_medico(self, client, db):
        from core_app.models import CustomUser, UserProfile

        paciente = CustomUser.objects.create_user(
            email="paciente@trathea.app",
            password="Senha@Segura123",
            nome_completo="Paciente Teste",
            role="paciente",
        )
        UserProfile.objects.create(user=paciente, cpf="11144477735")

        client.force_authenticate(user=paciente)

        # Tentar criar receita (rota de médico)
        url = reverse("receita-list-create")
        response = client.post(url, {})

        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)
