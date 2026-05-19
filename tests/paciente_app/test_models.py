"""
tests/paciente_app/test_models.py
Testes unitários para os modelos do paciente_app.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, PropertyMock

from paciente_app.models import Paciente, Prontuario, SolicitacaoConsulta


@pytest.mark.django_db
class TestPaciente:
    """Testes do modelo Paciente."""

    def test_criar_paciente(self, paciente):
        assert paciente.pk is not None
        assert paciente.tipo_sanguineo == "O+"
        assert paciente.peso_kg == Decimal("70.50")
        assert paciente.altura_cm == 175
        assert paciente.alergias == "Dipirona"
        assert paciente.convenio_nome == "Unimed"

    def test_str_representation(self, paciente):
        assert "Maria Santos" in str(paciente)

    def test_property_idade(self, paciente):
        idade = paciente.idade
        assert isinstance(idade, int)
        assert idade >= 0
        # Nascido em 1990 — em 2026 teria 35 ou 36
        assert 35 <= idade <= 36

    def test_property_cpf_mascarado(self, paciente):
        cpf_mask = paciente.cpf_mascarado
        assert cpf_mask.startswith("***.")
        assert cpf_mask.endswith("***-**")
        # Verifica que mostra os dígitos centrais
        assert "444" in cpf_mask

    def test_cpf_mascarado_sem_cpf(self, usuario_paciente):
        """Testa CPF mascarado quando o perfil não tem CPF."""
        usuario_paciente.profile.cpf = ""
        usuario_paciente.profile.save()

        paciente = Paciente.objects.create(
            user=usuario_paciente,
            data_nascimento=date(1990, 5, 15),
        )
        assert paciente.cpf_mascarado == "***.***.***-**"

    def test_get_summary(self, paciente):
        summary = paciente.get_summary()
        assert "id" in summary
        assert "nome" in summary
        assert "idade" in summary
        assert "cpf" in summary
        assert summary["nome"] == "Maria Santos"

    def test_notificacoes_padrao(self, paciente):
        assert paciente.notificacoes_whatsapp is True
        assert paciente.notificacoes_email is True

    def test_tipos_sanguineos_validos(self):
        choices = dict(Paciente._meta.get_field("tipo_sanguineo").choices)
        tipos_esperados = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
        assert set(choices.keys()) == tipos_esperados


@pytest.mark.django_db
class TestProntuario:
    """Testes do modelo Prontuário."""

    def test_criar_prontuario(self, paciente, medico):
        from django.utils import timezone

        prontuario = Prontuario.objects.create(
            paciente=paciente,
            medico=medico,
            data_consulta=timezone.now(),
            queixa_principal="Dor de cabeça persistente",
            anamnese="Paciente relata cefaleia há 3 dias",
            hipotese_diagnostica="Enxaqueca",
            diagnostico_cid10="G43",
            conduta="Prescrição de analgésicos",
        )
        assert prontuario.pk is not None
        assert "Dor de cabeça" in prontuario.queixa_principal

    def test_str_representation(self, paciente, medico):
        from django.utils import timezone

        prontuario = Prontuario.objects.create(
            paciente=paciente,
            medico=medico,
            data_consulta=timezone.now(),
            queixa_principal="Teste",
        )
        assert "Prontuário" in str(prontuario)

    def test_ordering_por_data_consulta(self, paciente, medico):
        from django.utils import timezone
        from datetime import timedelta

        p1 = Prontuario.objects.create(
            paciente=paciente, medico=medico,
            data_consulta=timezone.now() - timedelta(days=10),
            queixa_principal="Antiga",
        )
        p2 = Prontuario.objects.create(
            paciente=paciente, medico=medico,
            data_consulta=timezone.now(),
            queixa_principal="Recente",
        )
        prontuarios = list(Prontuario.objects.filter(paciente=paciente))
        assert prontuarios[0] == p2  # Mais recente primeiro


@pytest.mark.django_db
class TestSolicitacaoConsulta:
    """Testes do modelo SolicitacaoConsulta."""

    def test_criar_solicitacao(self, paciente, medico):
        solicitacao = SolicitacaoConsulta.objects.create(
            paciente=paciente,
            medico=medico,
            data_preferencia=date(2026, 5, 1),
            periodo_preferencia="manha",
            motivo="Consulta de rotina",
        )
        assert solicitacao.pk is not None
        assert solicitacao.status == "pendente"

    def test_status_default_pendente(self, paciente, medico):
        solicitacao = SolicitacaoConsulta.objects.create(
            paciente=paciente,
            medico=medico,
            data_preferencia=date(2026, 5, 1),
            periodo_preferencia="tarde",
            motivo="Retorno",
        )
        assert solicitacao.status == SolicitacaoConsulta.Status.PENDENTE

    def test_str_representation(self, paciente, medico):
        solicitacao = SolicitacaoConsulta.objects.create(
            paciente=paciente,
            medico=medico,
            data_preferencia=date(2026, 5, 1),
            periodo_preferencia="manha",
            motivo="Exame",
        )
        assert "Pendente" in str(solicitacao)

    def test_periodos_validos(self):
        periodos = {c[0] for c in SolicitacaoConsulta.PeriodoPref.choices}
        assert periodos == {"manha", "tarde", "noite"}

    def test_status_possiveis(self):
        statuses = {c[0] for c in SolicitacaoConsulta.Status.choices}
        assert statuses == {"pendente", "aceita", "recusada", "novo_horario"}
