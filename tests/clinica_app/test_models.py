"""
tests/clinica_app/test_models.py
Testes unitários para os modelos do clinica_app.
"""
import pytest
from django.db import IntegrityError

from clinica_app.models import Clinica, Secretaria


@pytest.mark.django_db
class TestClinica:
    """Testes do modelo Clinica."""

    def test_criar_clinica(self, clinica):
        assert clinica.pk is not None
        assert clinica.nome_fantasia == "Clínica Saúde Total"
        assert clinica.cnpj == "11222333000181"
        assert clinica.ativa is True

    def test_str_representation(self, clinica):
        assert str(clinica) == "Clínica Saúde Total"

    def test_cnpj_unico(self, clinica, db):
        from core_app.models import CustomUser, UserProfile

        user2 = CustomUser.objects.create_user(
            email="clinica2@tratta.app", password="Senha@Segura123",
            nome_completo="Clinica 2", role="clinica",
        )
        UserProfile.objects.create(user=user2, cpf=None)
        with pytest.raises(IntegrityError):
            Clinica.objects.create(
                user=user2,
                nome_fantasia="Outra Clínica",
                cnpj="11222333000181",  # Mesmo CNPJ
            )

    def test_adicionar_medico_a_clinica(self, clinica, medico):
        clinica.medicos.add(medico)
        assert medico in clinica.medicos.all()
        assert clinica.medicos.count() == 1

    def test_campos_opcionais_vazios(self, clinica):
        assert clinica.latitude is None
        assert clinica.longitude is None
        assert clinica.protocolo_manchester_ativo is False


@pytest.mark.django_db
class TestSecretaria:
    """Testes do modelo Secretaria."""

    def test_criar_secretaria(self, usuario_secretaria, clinica):
        secretaria = usuario_secretaria.secretaria
        assert secretaria.clinica == clinica
        assert secretaria.pode_agendar is True
        assert secretaria.pode_ver_prontuario is False

    def test_str_representation(self, usuario_secretaria):
        s = str(usuario_secretaria.secretaria)
        assert "Ana Secretária" in s
        assert "Saúde Total" in s
