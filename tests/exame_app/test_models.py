"""
tests/exame_app/test_models.py
Testes unitários para os modelos do exame_app.
"""
import pytest
from datetime import date

from exame_app.models import TipoExame, SolicitacaoExame


@pytest.mark.django_db
class TestTipoExame:
    """Testes do modelo TipoExame."""

    def test_criar_tipo_exame(self, tipo_exame):
        assert tipo_exame.pk is not None
        assert tipo_exame.nome == "Hemograma Completo"
        assert tipo_exame.requer_jejum is True
        assert tipo_exame.codigo_cbhpm == "40304361"

    def test_str_representation(self, tipo_exame):
        assert str(tipo_exame) == "Hemograma Completo"


@pytest.mark.django_db
class TestSolicitacaoExame:
    """Testes do modelo SolicitacaoExame."""

    def test_criar_solicitacao(self, solicitacao_exame):
        assert solicitacao_exame.pk is not None
        assert solicitacao_exame.status == "solicitado"
        assert solicitacao_exame.urgente is False

    def test_str_representation(self, solicitacao_exame):
        s = str(solicitacao_exame)
        assert "Hemograma" in s

    def test_status_choices(self):
        statuses = {c[0] for c in SolicitacaoExame.Status.choices}
        assert statuses == {"solicitado", "realizado", "resultado_disponivel", "cancelado"}

    def test_alterar_para_realizado(self, solicitacao_exame):
        solicitacao_exame.status = "realizado"
        solicitacao_exame.data_realizacao = date(2026, 4, 15)
        solicitacao_exame.save()
        solicitacao_exame.refresh_from_db()
        assert solicitacao_exame.status == "realizado"
        assert solicitacao_exame.data_realizacao == date(2026, 4, 15)

    def test_ordering_por_data_solicitacao(self, consulta, paciente, medico, tipo_exame):
        s1 = SolicitacaoExame.objects.create(
            consulta=consulta, paciente=paciente, medico=medico,
            tipo_exame=tipo_exame, instrucoes="Primeiro",
        )
        s2 = SolicitacaoExame.objects.create(
            consulta=consulta, paciente=paciente, medico=medico,
            tipo_exame=tipo_exame, instrucoes="Segundo",
        )
        exames = list(SolicitacaoExame.objects.filter(paciente=paciente))
        # Ordering é -data_solicitacao, mais recente primeiro
        assert exames[0] == s2
