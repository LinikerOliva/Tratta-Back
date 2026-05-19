"""
tests/core_app/test_serializers.py
Testes dos serializers do core_app (Register, Login, Profile).
"""
import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory

from core_app.models import CustomUser, UserProfile
from core_app.serializers import (
    RegisterSerializer,
    CustomUserSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)


@pytest.mark.django_db
class TestRegisterSerializer:
    """Testes do RegisterSerializer."""

    def _make_request(self, user=None):
        factory = APIRequestFactory()
        req = factory.post("/api/auth/register/")
        req.user = user or MagicMock(is_authenticated=False)
        return req

    def test_registro_valido_paciente(self):
        data = {
            "email": "novo@tratta.app",
            "nome_completo": "Novo Paciente",
            "role": "paciente",
            "password": "Senha@Segura123",
            "password_confirm": "Senha@Segura123",
            "cpf": "98765432100",
        }
        serializer = RegisterSerializer(
            data=data,
            context={"request": self._make_request()},
        )
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.email == "novo@tratta.app"
        assert user.role == "paciente"
        assert user.profile.cpf == "98765432100"

    def test_senhas_diferentes_falha(self):
        data = {
            "email": "teste@tratta.app",
            "nome_completo": "Teste",
            "role": "paciente",
            "password": "Senha@Segura123",
            "password_confirm": "SenhaDiferente123!",
            "cpf": "98765432100",
        }
        serializer = RegisterSerializer(
            data=data,
            context={"request": self._make_request()},
        )
        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors

    def test_cpf_invalido_falha(self):
        data = {
            "email": "teste@tratta.app",
            "nome_completo": "Teste",
            "role": "paciente",
            "password": "Senha@Segura123",
            "password_confirm": "Senha@Segura123",
            "cpf": "00000000000",
        }
        serializer = RegisterSerializer(
            data=data,
            context={"request": self._make_request()},
        )
        assert not serializer.is_valid()
        assert "cpf" in serializer.errors

    def test_email_duplicado_falha(self, usuario_paciente):
        data = {
            "email": "paciente@tratta.app",
            "nome_completo": "Duplicado",
            "role": "paciente",
            "password": "Senha@Segura123",
            "password_confirm": "Senha@Segura123",
            "cpf": "52998224725",
        }
        serializer = RegisterSerializer(
            data=data,
            context={"request": self._make_request()},
        )
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_role_admin_sem_permissao_falha(self):
        data = {
            "email": "hacker@tratta.app",
            "nome_completo": "Hacker",
            "role": "admin",
            "password": "Senha@Segura123",
            "password_confirm": "Senha@Segura123",
            "cpf": "52998224725",
        }
        serializer = RegisterSerializer(
            data=data,
            context={"request": self._make_request()},
        )
        assert not serializer.is_valid()
        assert "role" in serializer.errors

    def test_nome_completo_sanitizado(self):
        data = {
            "email": "xss@tratta.app",
            "nome_completo": '<script>alert("xss")</script>Maria',
            "role": "paciente",
            "password": "Senha@Segura123",
            "password_confirm": "Senha@Segura123",
            "cpf": "52998224725",
        }
        serializer = RegisterSerializer(
            data=data,
            context={"request": self._make_request()},
        )
        assert serializer.is_valid(), serializer.errors
        # O nome deve ter sido escapado
        assert "<script>" not in serializer.validated_data["nome_completo"]


@pytest.mark.django_db
class TestCustomUserSerializer:
    """Testes do CustomUserSerializer."""

    def test_serializa_usuario_completo(self, usuario_medico):
        serializer = CustomUserSerializer(usuario_medico)
        data = serializer.data
        assert data["email"] == "dr.silva@tratta.app"
        assert data["nome_completo"] == "Dr. Carlos Silva"
        assert data["role"] == "medico"
        assert "profile" in data
        assert "password" not in data  # Senha NUNCA aparece

    def test_campos_somente_leitura(self, usuario_medico):
        serializer = CustomUserSerializer(usuario_medico)
        read_only = serializer.Meta.read_only_fields
        assert "id" in read_only
        assert "date_joined" in read_only
        assert "is_verified" in read_only


@pytest.mark.django_db
class TestUserProfileSerializer:
    """Testes do UserProfileSerializer."""

    def test_validacao_cpf_invalido(self):
        serializer = UserProfileSerializer(data={"cpf": "12345678900"})
        assert not serializer.is_valid()
        assert "cpf" in serializer.errors

    def test_validacao_cpf_valido(self):
        serializer = UserProfileSerializer(data={"cpf": "987.654.321-00"})
        serializer.is_valid()
        # Este teste valida só o campo CPF — o serializer pode ter outros erros
        if "cpf" in serializer.errors:
            pytest.fail(f"CPF válido rejeitado: {serializer.errors['cpf']}")
