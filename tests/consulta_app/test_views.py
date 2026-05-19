"""
tests/consulta_app/test_views.py
Testes das views/API do consulta_app.
"""
import pytest
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status


@pytest.mark.django_db
class TestAgendamentoViews:
    """Testes dos endpoints de Agendamento."""

    def test_listar_agendamentos_medico(self, auth_client, medico, agendamento):
        url = reverse("agendamento-list")
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_criar_agendamento(self, auth_client, medico, paciente, clinica):
        url = reverse("agendamento-list")
        data = {
            "paciente": paciente.pk,
            "medico": medico.pk,
            "clinica": clinica.pk,
            "data_hora": (timezone.now() + timedelta(days=3)).isoformat(),
            "motivo": "Consulta nova",
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_detalhe_agendamento(self, auth_client, medico, agendamento):
        url = reverse("agendamento-detail", kwargs={"pk": agendamento.pk})
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["motivo"] == "Consulta de rotina"

    def test_atualizar_status_agendamento(self, auth_client, medico, agendamento):
        url = reverse("agendamento-detail", kwargs={"pk": agendamento.pk})
        response = auth_client.patch(url, {"status": "confirmado"}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_filtro_por_status(self, auth_client, medico, agendamento):
        url = reverse("agendamento-list")
        response = auth_client.get(url, {"status": "pendente"})
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestConsultaViews:
    """Testes dos endpoints de Consulta."""

    def test_listar_consultas(self, auth_client, medico, consulta):
        url = reverse("consulta-list")
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_criar_consulta(self, auth_client, medico, paciente, agendamento):
        url = reverse("consulta-list")
        data = {
            "agendamento": agendamento.pk,
            "paciente": paciente.pk,
            "medico": medico.pk,
            "data_inicio": timezone.now().isoformat(),
            "resumo": "Inicio da consulta",
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_paciente_nao_cria_consulta(self, paciente_client, paciente, medico, agendamento):
        url = reverse("consulta-list")
        data = {
            "agendamento": agendamento.pk,
            "paciente": paciente.pk,
            "medico": medico.pk,
            "data_inicio": timezone.now().isoformat(),
        }
        response = paciente_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_detalhe_consulta(self, auth_client, medico, consulta):
        url = reverse("consulta-detail", kwargs={"pk": consulta.pk})
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_finalizar_consulta(self, auth_client, medico, consulta):
        url = reverse("consulta-detail", kwargs={"pk": consulta.pk})
        response = auth_client.patch(url, {"status": "finalizada"}, format="json")
        assert response.status_code == status.HTTP_200_OK
