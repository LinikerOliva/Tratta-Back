"""
tests/trathea_core/test_permissions.py
Testes das permissões RBAC do trathea_core.
"""
import pytest
from unittest.mock import MagicMock

from trathea_core.auth.permissions import (
    IsDoctor,
    IsPatient,
    IsClinic,
    IsSecretary,
    IsAdminUser,
    IsDoctorOrReadOnly,
    IsDoctorOrAdmin,
    IsMedicalStaff,
    IsOwner,
)


def _make_request(user=None, method="GET"):
    request = MagicMock()
    request.user = user or MagicMock(is_authenticated=False)
    request.method = method
    return request


def _make_user(role, is_authenticated=True, is_active=True):
    user = MagicMock()
    user.role = role
    user.is_authenticated = is_authenticated
    user.is_active = is_active
    return user


class TestIsDoctor:
    def test_medico_tem_permissao(self):
        user = _make_user("medico")
        request = _make_request(user)
        assert IsDoctor().has_permission(request, None) is True

    def test_paciente_nao_tem_permissao(self):
        user = _make_user("paciente")
        request = _make_request(user)
        assert IsDoctor().has_permission(request, None) is False

    def test_usuario_inativo_nao_tem_permissao(self):
        user = _make_user("medico", is_active=False)
        request = _make_request(user)
        assert IsDoctor().has_permission(request, None) is False


class TestIsPatient:
    def test_paciente_tem_permissao(self):
        user = _make_user("paciente")
        request = _make_request(user)
        assert IsPatient().has_permission(request, None) is True

    def test_medico_nao_tem_permissao(self):
        user = _make_user("medico")
        request = _make_request(user)
        assert IsPatient().has_permission(request, None) is False


class TestIsClinic:
    def test_clinica_tem_permissao(self):
        user = _make_user("clinica")
        request = _make_request(user)
        assert IsClinic().has_permission(request, None) is True


class TestIsSecretary:
    def test_secretaria_tem_permissao(self):
        user = _make_user("secretaria")
        request = _make_request(user)
        assert IsSecretary().has_permission(request, None) is True


class TestIsAdminUser:
    def test_admin_tem_permissao(self):
        user = _make_user("admin")
        request = _make_request(user)
        assert IsAdminUser().has_permission(request, None) is True

    def test_medico_nao_e_admin(self):
        user = _make_user("medico")
        request = _make_request(user)
        assert IsAdminUser().has_permission(request, None) is False


class TestIsDoctorOrReadOnly:
    def test_medico_pode_escrever(self):
        user = _make_user("medico")
        request = _make_request(user, method="POST")
        assert IsDoctorOrReadOnly().has_permission(request, None) is True

    def test_paciente_pode_ler(self):
        user = _make_user("paciente")
        request = _make_request(user, method="GET")
        assert IsDoctorOrReadOnly().has_permission(request, None) is True

    def test_paciente_nao_pode_escrever(self):
        user = _make_user("paciente")
        request = _make_request(user, method="POST")
        assert IsDoctorOrReadOnly().has_permission(request, None) is False


class TestIsDoctorOrAdmin:
    def test_medico_tem_permissao(self):
        user = _make_user("medico")
        request = _make_request(user)
        assert IsDoctorOrAdmin().has_permission(request, None) is True

    def test_admin_tem_permissao(self):
        user = _make_user("admin")
        request = _make_request(user)
        assert IsDoctorOrAdmin().has_permission(request, None) is True

    def test_paciente_sem_permissao(self):
        user = _make_user("paciente")
        request = _make_request(user)
        assert IsDoctorOrAdmin().has_permission(request, None) is False


class TestIsMedicalStaff:
    def test_medico_ok(self):
        for role in ("medico", "secretaria", "clinica", "admin"):
            user = _make_user(role)
            request = _make_request(user)
            assert IsMedicalStaff().has_permission(request, None) is True, f"Falhou para {role}"

    def test_paciente_nao_e_staff(self):
        user = _make_user("paciente")
        request = _make_request(user)
        assert IsMedicalStaff().has_permission(request, None) is False


class TestIsOwner:
    def test_dono_tem_permissao(self):
        user = _make_user("paciente")
        obj = MagicMock()
        obj.user = user
        request = _make_request(user)
        assert IsOwner().has_object_permission(request, None, obj) is True

    def test_outro_usuario_sem_permissao(self):
        user = _make_user("paciente")
        outro = _make_user("paciente")
        obj = MagicMock()
        obj.user = outro
        request = _make_request(user)
        assert IsOwner().has_object_permission(request, None, obj) is False
