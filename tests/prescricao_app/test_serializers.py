"""
tests/prescricao_app/test_serializers.py
Testes dos serializers do prescricao_app.
"""
import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory

from prescricao_app.models import Receita, ItemReceita, Medicamento
from prescricao_app.serializers import (
    ReceitaSerializer,
    ReceitaCreateSerializer,
    ItemReceitaSerializer,
    MedicamentoSerializer,
)


@pytest.mark.django_db
class TestReceitaCreateSerializer:
    """Testes do serializer de criação de receita."""

    def _make_request(self, user):
        factory = APIRequestFactory()
        req = factory.post("/api/receitas/")
        req.user = user
        return req

    def test_criar_receita_valida(self, medico, paciente, consulta, medicamento):
        data = {
            "tipo": "simples",
            "paciente": paciente.pk,
            "consulta": consulta.pk,
            "observacoes": "Tomar após refeições",
            "validade_dias": 30,
            "itens": [
                {
                    "medicamento_id": medicamento.pk,
                    "dosagem": "500mg",
                    "quantidade": "20 comprimidos",
                    "posologia": "1 comp de 8/8h",
                    "via_administracao": "oral",
                    "duracao_tratamento": "7 dias",
                    "ordem": 1,
                },
            ],
        }
        request = self._make_request(medico.user)
        serializer = ReceitaCreateSerializer(
            data=data,
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        receita = serializer.save()
        assert receita.tipo == "simples"
        assert receita.itens.count() == 1

    def test_receita_sem_itens_falha(self, medico, paciente, consulta):
        data = {
            "tipo": "simples",
            "paciente": paciente.pk,
            "consulta": consulta.pk,
            "itens": [],
        }
        request = self._make_request(medico.user)
        serializer = ReceitaCreateSerializer(
            data=data,
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "itens" in serializer.errors

    def test_receita_com_mais_de_20_itens_falha(self, medico, paciente, consulta, medicamento):
        itens = [
            {
                "medicamento_id": medicamento.pk,
                "dosagem": "500mg",
                "quantidade": "10",
                "posologia": "1x/dia",
                "ordem": i,
            }
            for i in range(21)
        ]
        data = {
            "tipo": "simples",
            "paciente": paciente.pk,
            "consulta": consulta.pk,
            "itens": itens,
        }
        request = self._make_request(medico.user)
        serializer = ReceitaCreateSerializer(
            data=data,
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "itens" in serializer.errors

    def test_receita_simples_com_controlado_falha(
        self, medico, paciente, consulta, medicamento_controlado
    ):
        data = {
            "tipo": "simples",
            "paciente": paciente.pk,
            "consulta": consulta.pk,
            "itens": [
                {
                    "medicamento_id": medicamento_controlado.pk,
                    "dosagem": "2mg",
                    "quantidade": "30",
                    "posologia": "1x à noite",
                    "ordem": 1,
                },
            ],
        }
        request = self._make_request(medico.user)
        serializer = ReceitaCreateSerializer(
            data=data,
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "tipo" in serializer.errors


@pytest.mark.django_db
class TestReceitaSerializer:
    """Testes do serializer de leitura de receita."""

    def test_serializar_receita_completa(self, receita):
        serializer = ReceitaSerializer(receita)
        data = serializer.data
        assert data["tipo"] == "simples"
        assert data["status"] == "rascunho"
        assert data["pode_ser_editada"] is True
        assert data["pode_ser_assinada"] is True
        assert len(data["itens"]) == 1
        assert "medico_nome" in data
        assert "paciente_nome" in data

    def test_campos_somente_leitura(self):
        read_only = ReceitaSerializer.Meta.read_only_fields
        assert "id" in read_only
        assert "status" in read_only
        assert "hash_verificacao" in read_only
        assert "assinada_em" in read_only


@pytest.mark.django_db
class TestItemReceitaSerializer:
    """Testes do serializer de item de receita."""

    def test_sanitizacao_posologia(self):
        serializer = ItemReceitaSerializer()
        result = serializer.validate_posologia('<script>alert("xss")</script>1 comp/dia')
        assert "<script>" not in result

    def test_sanitizacao_instrucoes_especiais(self):
        serializer = ItemReceitaSerializer()
        result = serializer.validate_instrucoes_especiais(
            '<iframe src="evil.com"></iframe>Tomar com água'
        )
        assert "<iframe" not in result
