"""
tests/medico_app/test_models.py
Testes unitários para os modelos do medico_app.
"""
import pytest
from datetime import time

from medico_app.models import Medico, Disponibilidade, ReceituarioConfig


@pytest.mark.django_db
class TestMedico:
    """Testes do modelo Medico."""

    def test_criar_medico(self, medico):
        assert medico.pk is not None
        assert medico.crm == "123456"
        assert medico.crm_estado == "SP"
        assert medico.especialidade == "Clínica Geral"

    def test_str_representation(self, medico):
        s = str(medico)
        assert "Dr(a)." in s
        assert "Carlos Silva" in s
        assert "CRM/SP" in s

    def test_property_nome_completo(self, medico):
        assert medico.nome_completo == "Dr. Carlos Silva"

    def test_property_pode_assinar_sem_govbr(self, medico):
        assert medico.pode_assinar is False

    def test_property_pode_assinar_com_govbr(self, medico):
        medico.is_govbr_linked = True
        medico.save()
        assert medico.pode_assinar is True

    def test_crm_unico(self, medico, db):
        from core_app.models import CustomUser, UserProfile
        from django.db import IntegrityError

        user2 = CustomUser.objects.create_user(
            email="dr2@tratta.app", password="Senha@Segura123",
            nome_completo="Dr. Segundo", role="medico",
        )
        UserProfile.objects.create(user=user2, cpf="52998224725")
        with pytest.raises(IntegrityError):
            Medico.objects.create(
                user=user2, crm="123456",  # Mesmo CRM
                crm_estado="SP", especialidade="Cardiologia",
            )

    def test_clinica_principal_nullable(self, medico):
        assert medico.clinica_principal is None

    def test_vincular_clinica(self, medico, clinica):
        medico.clinica_principal = clinica
        medico.save()
        medico.refresh_from_db()
        assert medico.clinica_principal == clinica


@pytest.mark.django_db
class TestDisponibilidade:
    """Testes do modelo Disponibilidade."""

    def test_criar_disponibilidade(self, disponibilidade):
        assert disponibilidade.pk is not None
        assert disponibilidade.dia_semana == 0
        assert disponibilidade.hora_inicio == time(8, 0)
        assert disponibilidade.hora_fim == time(12, 0)
        assert disponibilidade.duracao_consulta_min == 30

    def test_str_representation(self, disponibilidade):
        s = str(disponibilidade)
        assert "Segunda-feira" in s

    def test_unique_together_constraint(self, medico):
        Disponibilidade.objects.create(
            medico=medico, dia_semana=1,
            hora_inicio=time(14, 0), hora_fim=time(18, 0),
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Disponibilidade.objects.create(
                medico=medico, dia_semana=1,
                hora_inicio=time(14, 0), hora_fim=time(18, 0),
            )

    def test_dias_semana_validos(self):
        dias = {c[0] for c in Disponibilidade.DiaSemana.choices}
        assert dias == {0, 1, 2, 3, 4, 5, 6}

    def test_disponibilidade_ativo_default(self, medico):
        disp = Disponibilidade.objects.create(
            medico=medico, dia_semana=2,
            hora_inicio=time(9, 0), hora_fim=time(12, 0),
        )
        assert disp.ativo is True


@pytest.mark.django_db
class TestReceituarioConfig:
    """Testes do ReceituarioConfig."""

    def test_criar_receituario_config(self, medico):
        config = ReceituarioConfig.objects.create(
            medico=medico,
            cabecalho="Dr. Carlos Silva - CRM/SP 123456",
            rodape="Clínica Saúde Total",
            fonte_nome="Times New Roman",
        )
        assert config.pk == medico.pk
        assert config.fonte_nome == "Times New Roman"
        assert config.margem_superior == 20  # default

    def test_str_representation(self, medico):
        config = ReceituarioConfig.objects.create(medico=medico)
        assert "Receituário" in str(config)
