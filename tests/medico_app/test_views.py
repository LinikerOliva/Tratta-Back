"""
tests/medico_app/test_views.py
Testes das views/API do medico_app.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestMedicoListView:
    """Testes GET /api/doctors/"""

    def test_listar_medicos_como_medico(self, auth_client, medico):
        url = reverse("medico-list")
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(response.data["data"]) >= 1

    def test_paciente_nao_lista_medicos(self, paciente_client, medico):
        url = reverse("medico-list")
        response = paciente_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filtro_por_especialidade(self, auth_client, medico):
        url = reverse("medico-list")
        response = auth_client.get(url, {"especialidade": "Clínica"})
        assert response.status_code == status.HTTP_200_OK
        for doc in response.data["data"]:
            assert "clínica" in doc["especialidade"].lower()


@pytest.mark.django_db
class TestMedicoDetailView:
    """Testes GET/PATCH /api/doctors/<pk>/"""

    def test_detalhe_medico(self, auth_client, medico):
        url = reverse("medico-detail", kwargs={"pk": medico.pk})
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["crm"] == "123456"

    def test_detalhe_medico_inexistente(self, auth_client, medico):
        url = reverse("medico-detail", kwargs={"pk": 99999})
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_atualizar_proprio_perfil(self, auth_client, medico):
        url = reverse("medico-detail", kwargs={"pk": medico.pk})
        response = auth_client.patch(url, {"bio": "Nova biografia"}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_nao_editar_perfil_de_outro(self, paciente_client, medico, paciente):
        url = reverse("medico-detail", kwargs={"pk": medico.pk})
        response = paciente_client.patch(url, {"bio": "Hacker"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestMeuPerfilMedicoView:
    """Testes GET/PATCH /api/doctors/me/"""

    def test_meu_perfil(self, auth_client, medico):
        url = reverse("medico-me")
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["crm"] == "123456"

    def test_atualizar_meu_perfil(self, auth_client, medico):
        url = reverse("medico-me")
        response = auth_client.patch(url, {"especialidade": "Cardiologia"}, format="json")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMedicoDisponibilidadeView:
    """Testes GET/POST /api/doctors/<pk>/agenda/"""

    def test_ver_agenda_publica(self, auth_client, medico, disponibilidade):
        url = reverse("medico-agenda", kwargs={"pk": medico.pk})
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) >= 1

    def test_adicionar_disponibilidade(self, auth_client, medico):
        url = reverse("medico-agenda", kwargs={"pk": medico.pk})
        data = {
            "dia_semana": 2,
            "hora_inicio": "14:00",
            "hora_fim": "18:00",
            "duracao_consulta_min": 30,
        }
        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_medico_nao_gerencia_agenda_de_outro(self, medico):
        from rest_framework.test import APIClient
        from core_app.models import CustomUser, UserProfile
        from medico_app.models import Medico

        outro_user = CustomUser.objects.create_user(
            email="outro.doc@tratta.app", password="Senha@Segura123",
            nome_completo="Outro Médico", role="medico",
        )
        UserProfile.objects.create(user=outro_user, cpf="52998224725")
        outro_medico = Medico.objects.create(
            user=outro_user, crm="654321", crm_estado="RJ",
            especialidade="Dermatologia",
        )

        client = APIClient()
        client.force_authenticate(user=outro_user)

        url = reverse("medico-agenda", kwargs={"pk": medico.pk})
        data = {
            "dia_semana": 3,
            "hora_inicio": "09:00",
            "hora_fim": "12:00",
            "duracao_consulta_min": 30,
        }
        response = client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
