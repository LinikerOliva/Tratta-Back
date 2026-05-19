"""
tests/admin_app/test_models.py
Testes unitários para os modelos do admin_app.
"""
import pytest
from admin_app.models import SolicitacaoCadastro


@pytest.mark.django_db
class TestSolicitacaoCadastro:
    """Testes do modelo SolicitacaoCadastro."""

    def test_criar_solicitacao_medico(self, usuario_medico):
        solicitacao = SolicitacaoCadastro.objects.create(
            solicitante=usuario_medico,
            tipo="medico",
            dados_adicionais={
                "crm": "123456",
                "crm_estado": "SP",
                "especialidade": "Clínica Geral",
            },
        )
        assert solicitacao.pk is not None
        assert solicitacao.status == "pendente"
        assert solicitacao.tipo == "medico"
        assert solicitacao.dados_adicionais["crm"] == "123456"

    def test_str_representation(self, usuario_medico):
        solicitacao = SolicitacaoCadastro.objects.create(
            solicitante=usuario_medico,
            tipo="medico",
            dados_adicionais={"crm": "123456"},
        )
        s = str(solicitacao)
        assert "medico" in s
        assert usuario_medico.email in s

    def test_aprovar_solicitacao(self, usuario_medico, usuario_admin):
        solicitacao = SolicitacaoCadastro.objects.create(
            solicitante=usuario_medico,
            tipo="medico",
            dados_adicionais={"crm": "123456"},
        )
        solicitacao.status = "aprovada"
        solicitacao.avaliado_por = usuario_admin
        solicitacao.save()
        solicitacao.refresh_from_db()
        assert solicitacao.status == "aprovada"
        assert solicitacao.avaliado_por == usuario_admin

    def test_rejeitar_solicitacao(self, usuario_medico, usuario_admin):
        solicitacao = SolicitacaoCadastro.objects.create(
            solicitante=usuario_medico,
            tipo="medico",
            dados_adicionais={"crm": "invalido"},
        )
        solicitacao.status = "rejeitada"
        solicitacao.avaliado_por = usuario_admin
        solicitacao.motivo_rejeicao = "CRM inválido"
        solicitacao.save()
        solicitacao.refresh_from_db()
        assert solicitacao.status == "rejeitada"
        assert solicitacao.motivo_rejeicao == "CRM inválido"

    def test_tipos_solicitacao(self):
        tipos = {c[0] for c in SolicitacaoCadastro.Tipo.choices}
        assert tipos == {"medico", "clinica", "secretaria"}

    def test_status_choices(self):
        statuses = {c[0] for c in SolicitacaoCadastro.Status.choices}
        assert statuses == {"pendente", "em_analise", "aprovada", "rejeitada"}

    def test_ordering_por_created_at(self, usuario_medico):
        s1 = SolicitacaoCadastro.objects.create(
            solicitante=usuario_medico, tipo="medico",
            dados_adicionais={"crm": "111111"},
        )
        s2 = SolicitacaoCadastro.objects.create(
            solicitante=usuario_medico, tipo="medico",
            dados_adicionais={"crm": "222222"},
        )
        solicitacoes = list(SolicitacaoCadastro.objects.all())
        assert solicitacoes[0] == s2  # Mais recente primeiro
