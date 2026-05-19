"""
tests/prescricao_app/test_models.py
Testes unitários para os modelos do prescricao_app.
"""
import pytest
from datetime import timedelta

from django.utils import timezone
from prescricao_app.models import Medicamento, Receita, ItemReceita, TemplateReceita


@pytest.mark.django_db
class TestMedicamento:
    """Testes do modelo Medicamento."""

    def test_criar_medicamento(self, medicamento):
        assert medicamento.pk is not None
        assert medicamento.nome == "Paracetamol"
        assert medicamento.tipo == "simples"
        assert medicamento.ativo is True

    def test_str_representation(self, medicamento):
        s = str(medicamento)
        assert "Paracetamol" in s
        assert "500mg" in s

    def test_tipos_medicamento(self):
        tipos = {c[0] for c in Medicamento.Tipo.choices}
        assert tipos == {"simples", "controlado", "antimicrobiano"}

    def test_medicamento_controlado(self, medicamento_controlado):
        assert medicamento_controlado.tipo == "controlado"
        assert medicamento_controlado.principio_ativo == "Clonazepam"


@pytest.mark.django_db
class TestReceita:
    """Testes do modelo Receita."""

    def test_criar_receita(self, receita):
        assert receita.pk is not None
        assert receita.tipo == "simples"
        assert receita.status == "rascunho"
        assert receita.validade_dias == 30

    def test_str_representation(self, receita):
        s = str(receita)
        assert "Receita" in s
        assert "simples" in s
        assert "rascunho" in s

    def test_itens_receita(self, receita):
        assert receita.itens.count() == 1
        item = receita.itens.first()
        assert item.medicamento.nome == "Paracetamol"
        assert item.dosagem == "500mg"

    def test_property_pode_ser_editada_rascunho(self, receita):
        assert receita.pode_ser_editada is True

    def test_property_pode_ser_editada_assinada(self, receita):
        receita.status = "assinada"
        receita.save()
        assert receita.pode_ser_editada is False

    def test_property_pode_ser_assinada(self, receita):
        assert receita.pode_ser_assinada is True
        receita.status = "emitida"
        assert receita.pode_ser_assinada is True
        receita.status = "assinada"
        assert receita.pode_ser_assinada is False

    def test_property_esta_expirada_nao(self, receita):
        # Receita recém-criada não está expirada
        assert receita.esta_expirada is False

    def test_status_choices(self):
        statuses = {c[0] for c in Receita.Status.choices}
        assert "rascunho" in statuses
        assert "assinada" in statuses
        assert "expirada" in statuses

    def test_tipo_choices(self):
        tipos = {c[0] for c in Receita.Tipo.choices}
        assert tipos == {"simples", "controlada", "antimicrobiano"}


@pytest.mark.django_db
class TestItemReceita:
    """Testes do modelo ItemReceita."""

    def test_str_representation(self, receita):
        item = receita.itens.first()
        s = str(item)
        assert "Paracetamol" in s
        assert "500mg" in s

    def test_ordering_por_ordem(self, receita, medicamento_controlado):
        # Adiciona outro item com ordem menor
        ItemReceita.objects.create(
            receita=receita,
            medicamento=medicamento_controlado,
            dosagem="2mg",
            quantidade="30 comprimidos",
            posologia="1 comp à noite",
            ordem=0,
        )
        itens = list(receita.itens.all())
        assert itens[0].ordem == 0
        assert itens[1].ordem == 1


@pytest.mark.django_db
class TestTemplateReceita:
    """Testes do modelo TemplateReceita."""

    def test_criar_template(self, medico):
        template = TemplateReceita.objects.create(
            medico=medico,
            nome="Gripe Comum",
            descricao="Template para sintomas gripais",
            tipo_receita="simples",
            itens_json=[
                {
                    "medicamento": "Paracetamol",
                    "dosagem": "500mg",
                    "posologia": "1 comp de 6/6h",
                },
            ],
            ativo=True,
        )
        assert template.pk is not None
        assert template.itens_json[0]["medicamento"] == "Paracetamol"

    def test_str_representation(self, medico):
        template = TemplateReceita.objects.create(
            medico=medico, nome="Cefaleia",
            tipo_receita="simples", itens_json=[],
        )
        assert "Template" in str(template)
        assert "Cefaleia" in str(template)
