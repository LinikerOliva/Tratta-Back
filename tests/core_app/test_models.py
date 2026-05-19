"""
tests/core_app/test_models.py
Testes unitários para os modelos do core_app (CustomUser, UserProfile).
"""
import pytest
from django.db import IntegrityError
from core_app.models import CustomUser, UserProfile


@pytest.mark.django_db
class TestCustomUser:
    """Testes do modelo CustomUser."""

    def test_criar_usuario_basico(self):
        user = CustomUser.objects.create_user(
            email="teste@tratta.app",
            password="Senha@123",
            nome_completo="Teste Silva",
            role="paciente",
        )
        assert user.pk is not None
        assert user.email == "teste@tratta.app"
        assert user.nome_completo == "Teste Silva"
        assert user.role == "paciente"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_email_normalizado(self):
        user = CustomUser.objects.create_user(
            email="Teste@TRATTA.App",
            password="Senha@123",
            nome_completo="Teste",
            role="paciente",
        )
        assert user.email == "Teste@tratta.app"

    def test_email_obrigatorio(self):
        with pytest.raises(ValueError, match="email"):
            CustomUser.objects.create_user(
                email="",
                password="Senha@123",
                nome_completo="Teste",
                role="paciente",
            )

    def test_email_unico(self):
        CustomUser.objects.create_user(
            email="unico@tratta.app", password="Senha@123",
            nome_completo="User 1", role="paciente",
        )
        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(
                email="unico@tratta.app", password="Senha@123",
                nome_completo="User 2", role="paciente",
            )

    def test_criar_superuser(self):
        admin = CustomUser.objects.create_superuser(
            email="superadmin@tratta.app",
            password="Admin@Segura123",
            nome_completo="Super Admin",
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.role == "admin"

    def test_str_representation(self, usuario_medico):
        expected = f"{usuario_medico.nome_completo} <{usuario_medico.email}> [{usuario_medico.role}]"
        assert str(usuario_medico) == expected

    def test_property_is_admin(self, usuario_admin):
        assert usuario_admin.is_admin is True
        assert usuario_admin.is_medico is False
        assert usuario_admin.is_paciente is False

    def test_property_is_medico(self, usuario_medico):
        assert usuario_medico.is_medico is True
        assert usuario_medico.is_admin is False

    def test_property_is_paciente(self, usuario_paciente):
        assert usuario_paciente.is_paciente is True
        assert usuario_paciente.is_medico is False

    def test_roles_validos(self):
        roles_esperados = {"admin", "medico", "paciente", "secretaria", "clinica"}
        roles_model = {choice[0] for choice in CustomUser.Role.choices}
        assert roles_model == roles_esperados

    def test_login_com_senha_correta(self, usuario_medico):
        assert usuario_medico.check_password("Senha@Segura123") is True

    def test_login_com_senha_errada(self, usuario_medico):
        assert usuario_medico.check_password("SenhaErrada") is False

    def test_ordering_por_date_joined(self):
        u1 = CustomUser.objects.create_user(
            email="primeiro@tratta.app", password="S@123abc",
            nome_completo="Primeiro", role="paciente",
        )
        u2 = CustomUser.objects.create_user(
            email="segundo@tratta.app", password="S@123abc",
            nome_completo="Segundo", role="paciente",
        )
        users = list(CustomUser.objects.filter(email__in=["primeiro@tratta.app", "segundo@tratta.app"]))
        # Ordering é -date_joined, mais recente primeiro
        assert users[0] == u2


@pytest.mark.django_db
class TestUserProfile:
    """Testes do modelo UserProfile."""

    def test_criar_perfil(self, usuario_paciente):
        profile = usuario_paciente.profile
        assert profile.cpf == "11144477735"

    def test_perfil_str(self, usuario_paciente):
        profile = usuario_paciente.profile
        assert "Maria Santos" in str(profile)

    def test_cpf_unico(self, usuario_paciente):
        outro_user = CustomUser.objects.create_user(
            email="outro@tratta.app", password="Senha@123",
            nome_completo="Outro", role="paciente",
        )
        with pytest.raises(IntegrityError):
            UserProfile.objects.create(user=outro_user, cpf="11144477735")

    def test_perfil_sem_cpf(self):
        user = CustomUser.objects.create_user(
            email="semcpf@tratta.app", password="Senha@123",
            nome_completo="Sem CPF", role="clinica",
        )
        profile = UserProfile.objects.create(user=user, cpf=None)
        assert profile.cpf is None

    def test_campos_endereco_em_branco(self, usuario_paciente):
        profile = usuario_paciente.profile
        assert profile.endereco_logradouro == ""
        assert profile.endereco_cidade == ""
        assert profile.endereco_estado == ""
        assert profile.endereco_cep == ""

    def test_2fa_desativado_por_padrao(self, usuario_paciente):
        profile = usuario_paciente.profile
        assert profile.is_2fa_enabled is False
