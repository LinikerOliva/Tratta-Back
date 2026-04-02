"""
clinica_app/views.py
Views do módulo Clínica e Secretaria.
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error, api_not_found, api_created
from trathea_core.auth.permissions import IsClinic, IsAdminUser, IsMedicalStaff

from .models import Clinica, Secretaria
from .serializers import ClinicaSerializer, ClinicaUpdateSerializer, SecretariaSerializer

logger = logging.getLogger("trathea")


class ClinicaListView(APIView):
    """GET /api/clinics/ — Lista clínicas ativas."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Clínicas"], summary="Listar clínicas")
    def get(self, request):
        nome = request.query_params.get("nome")
        qs = Clinica.objects.prefetch_related("medicos").filter(ativa=True)
        if nome:
            qs = qs.filter(nome_fantasia__icontains=nome)
        serializer = ClinicaSerializer(qs, many=True)
        return api_success(data=serializer.data)


class ClinicaDetailView(APIView):
    """GET/PATCH /api/clinics/<pk>/ — Detalhes e atualização de clínica."""

    permission_classes = [IsAuthenticated]

    def _get_clinica(self, pk):
        try:
            return Clinica.objects.prefetch_related("medicos").get(pk=pk)
        except Clinica.DoesNotExist:
            return None

    @extend_schema(tags=["Clínicas"], summary="Detalhes da clínica")
    def get(self, request, pk):
        clinica = self._get_clinica(pk)
        if not clinica:
            return api_not_found("Clínica não encontrada.")
        serializer = ClinicaSerializer(clinica)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Clínicas"], summary="Atualizar clínica")
    def patch(self, request, pk):
        clinica = self._get_clinica(pk)
        if not clinica:
            return api_not_found("Clínica não encontrada.")
        if clinica.user != request.user and request.user.role != "admin":
            return api_error("Você só pode editar sua própria clínica.", http_status=403)
        serializer = ClinicaUpdateSerializer(clinica, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=ClinicaSerializer(clinica).data, message="Clínica atualizada.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class MinhaClinicaView(APIView):
    """GET/PATCH /api/clinics/me/ — A clínica acessa seu próprio perfil."""

    permission_classes = [IsAuthenticated, IsClinic]

    @extend_schema(tags=["Clínicas"], summary="Minha clínica")
    def get(self, request):
        try:
            clinica = request.user.clinica
        except Clinica.DoesNotExist:
            return api_not_found("Perfil de clínica não encontrado.")
        return api_success(data=ClinicaSerializer(clinica).data)

    @extend_schema(tags=["Clínicas"], summary="Atualizar minha clínica")
    def patch(self, request):
        try:
            clinica = request.user.clinica
        except Clinica.DoesNotExist:
            return api_not_found("Perfil de clínica não encontrado.")
        serializer = ClinicaUpdateSerializer(clinica, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=ClinicaSerializer(clinica).data, message="Clínica atualizada.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class ClinicaAdicionarMedicoView(APIView):
    """POST /api/clinics/<pk>/medicos/ — Adiciona médico à clínica."""

    permission_classes = [IsAuthenticated, IsClinic]

    @extend_schema(tags=["Clínicas"], summary="Adicionar médico à clínica")
    def post(self, request, pk):
        try:
            clinica = Clinica.objects.get(pk=pk)
        except Clinica.DoesNotExist:
            return api_not_found("Clínica não encontrada.")
        if clinica.user != request.user:
            return api_error("Você só pode gerenciar sua própria clínica.", http_status=403)
        medico_id = request.data.get("medico_id")
        if not medico_id:
            return api_error("Informe o medico_id.")
        try:
            from medico_app.models import Medico
            medico = Medico.objects.get(pk=medico_id)
        except Exception:
            return api_not_found("Médico não encontrado.")
        clinica.medicos.add(medico)
        return api_success(message=f"Dr(a). {medico.user.nome_completo} adicionado(a) à clínica.")


# ── Secretaria ────────────────────────────────────────────────────────────────

class SecretariaListView(APIView):
    """GET /api/secretarias/ — Lista secretarias (admin e clínica)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Secretarias"], summary="Listar secretarias")
    def get(self, request):
        if request.user.role == "clinica":
            try:
                qs = Secretaria.objects.filter(clinica=request.user.clinica)
            except Exception:
                qs = Secretaria.objects.none()
        elif request.user.role == "admin":
            qs = Secretaria.objects.select_related("user", "clinica").all()
        else:
            return api_error("Acesso negado.", http_status=403)
        serializer = SecretariaSerializer(qs, many=True)
        return api_success(data=serializer.data)


class SecretariaDetailView(APIView):
    """GET /api/secretarias/<pk>/ — Detalhes da secretaria."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Secretarias"], summary="Detalhes da secretaria")
    def get(self, request, pk):
        try:
            secretaria = Secretaria.objects.select_related("user", "clinica").get(pk=pk)
        except Secretaria.DoesNotExist:
            return api_not_found("Secretaria não encontrada.")
        if request.user.role not in ("admin", "clinica"):
            if not hasattr(request.user, "secretaria") or request.user.secretaria != secretaria:
                return api_error("Acesso negado.", http_status=403)
        serializer = SecretariaSerializer(secretaria)
        return api_success(data=serializer.data)
