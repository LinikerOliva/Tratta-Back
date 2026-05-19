"""
tests/consulta_app/test_models.py
Testes unitários para os modelos do consulta_app.
"""
import pytest
from datetime import timedelta

from django.utils import timezone
from consulta_app.models import Agendamento, Consulta


@pytest.mark.django_db
class TestAgendamento:
    """Testes do modelo Agendamento."""

    def test_criar_agendamento(self, agendamento):
        assert agendamento.pk is not None
        assert agendamento.status == "pendente"
        assert agendamento.motivo == "Consulta de rotina"

    def test_str_representation(self, agendamento):
        s = str(agendamento)
        assert "Agendamento" in s

    def test_status_choices(self):
        statuses = {c[0] for c in Agendamento.Status.choices}
        assert statuses == {"pendente", "confirmado", "cancelado", "reagendado"}

    def test_alterar_status_para_confirmado(self, agendamento):
        agendamento.status = "confirmado"
        agendamento.save()
        agendamento.refresh_from_db()
        assert agendamento.status == "confirmado"

    def test_ordering_por_data_hora(self, paciente, medico, clinica):
        a1 = Agendamento.objects.create(
            paciente=paciente, medico=medico, clinica=clinica,
            data_hora=timezone.now() + timedelta(days=10),
            motivo="Futura",
        )
        a2 = Agendamento.objects.create(
            paciente=paciente, medico=medico, clinica=clinica,
            data_hora=timezone.now() + timedelta(days=1),
            motivo="Próxima",
        )
        agendamentos = list(Agendamento.objects.filter(paciente=paciente))
        assert agendamentos[0] == a2  # Mais cedo primeiro


@pytest.mark.django_db
class TestConsulta:
    """Testes do modelo Consulta."""

    def test_criar_consulta(self, consulta):
        assert consulta.pk is not None
        assert consulta.status == "em_andamento"
        assert consulta.resumo != ""

    def test_str_representation(self, consulta):
        s = str(consulta)
        assert "Consulta" in s

    def test_status_choices(self):
        statuses = {c[0] for c in Consulta.Status.choices}
        assert statuses == {"em_andamento", "finalizada", "cancelada"}

    def test_finalizar_consulta(self, consulta):
        consulta.status = "finalizada"
        consulta.data_fim = timezone.now()
        consulta.duracao_segundos = 1800  # 30 min
        consulta.save()
        consulta.refresh_from_db()
        assert consulta.status == "finalizada"
        assert consulta.data_fim is not None
        assert consulta.duracao_segundos == 1800

    def test_campos_ia_inicialmente_vazios(self, consulta):
        assert consulta.transcricao_texto == ""
        assert consulta.queixa_principal == ""
        assert consulta.anamnese == ""
        assert consulta.hipotese_diagnostica == ""

    def test_preencher_campos_ia(self, consulta):
        consulta.transcricao_texto = "Paciente relata dor."
        consulta.queixa_principal = "Dor de cabeça"
        consulta.anamnese = "Histórico de enxaqueca familiar."
        consulta.hipotese_diagnostica = "Enxaqueca com aura"
        consulta.save()
        consulta.refresh_from_db()
        assert consulta.queixa_principal == "Dor de cabeça"
