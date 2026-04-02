"""
paciente_app/views.py
Views do módulo Paciente e Prontuário.
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error, api_not_found, api_created
from trathea_core.auth.permissions import IsDoctor, IsPatient, IsMedicalStaff, CanAccessPatientData

from .models import Paciente, Prontuario
from .serializers import PacienteSerializer, PacienteUpdateSerializer, ProntuarioSerializer

logger = logging.getLogger("trathea")


class PacienteListView(APIView):
    """GET /api/patients/ — Lista pacientes (médicos, secretarias e admin)."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    @extend_schema(tags=["Pacientes"], summary="Listar pacientes")
    def get(self, request):
        nome = request.query_params.get("nome")
        qs = Paciente.objects.select_related("user", "medico_principal__user").all()
        # Médico vê apenas seus pacientes
        if request.user.role == "medico":
            try:
                qs = qs.filter(medico_principal=request.user.medico)
            except Exception:
                qs = qs.none()
        if nome:
            qs = qs.filter(user__nome_completo__icontains=nome)
        serializer = PacienteSerializer(qs, many=True)
        return api_success(data=serializer.data)


class PacienteDetailView(APIView):
    """GET/PATCH /api/patients/<pk>/ — Detalhes e atualização do paciente."""

    permission_classes = [IsAuthenticated]

    def _get_paciente(self, pk):
        try:
            return Paciente.objects.select_related("user", "medico_principal__user").get(pk=pk)
        except Paciente.DoesNotExist:
            return None

    @extend_schema(tags=["Pacientes"], summary="Detalhes do paciente")
    def get(self, request, pk):
        paciente = self._get_paciente(pk)
        if not paciente:
            return api_not_found("Paciente não encontrado.")
        # Paciente só vê seus próprios dados
        if request.user.role == "paciente" and paciente.user != request.user:
            return api_error("Acesso negado.", http_status=403)
        serializer = PacienteSerializer(paciente)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Pacientes"], summary="Atualizar dados do paciente")
    def patch(self, request, pk):
        paciente = self._get_paciente(pk)
        if not paciente:
            return api_not_found("Paciente não encontrado.")
        if request.user.role == "paciente" and paciente.user != request.user:
            return api_error("Você só pode editar seus próprios dados.", http_status=403)
        serializer = PacienteUpdateSerializer(paciente, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=PacienteSerializer(paciente).data, message="Dados atualizados.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class MeuPerfilPacienteView(APIView):
    """GET/PATCH /api/patients/me/ — Paciente acessa seu próprio perfil."""

    permission_classes = [IsAuthenticated, IsPatient]

    @extend_schema(tags=["Pacientes"], summary="Meu perfil de paciente")
    def get(self, request):
        try:
            paciente = request.user.paciente
        except Paciente.DoesNotExist:
            return api_not_found("Perfil de paciente não encontrado.")
        return api_success(data=PacienteSerializer(paciente).data)

    @extend_schema(tags=["Pacientes"], summary="Atualizar meu perfil de paciente")
    def patch(self, request):
        try:
            paciente = request.user.paciente
        except Paciente.DoesNotExist:
            return api_not_found("Perfil de paciente não encontrado.")
        serializer = PacienteUpdateSerializer(paciente, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=PacienteSerializer(paciente).data, message="Perfil atualizado.")
        return api_error("Dados inválidos.", errors=serializer.errors)


# ── Prontuários ───────────────────────────────────────────────────────────────

class ProntuarioListView(APIView):
    """GET/POST /api/prontuarios/ — Lista e cria prontuários."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    @extend_schema(tags=["Prontuários"], summary="Listar prontuários")
    def get(self, request):
        paciente_id = request.query_params.get("paciente")
        qs = Prontuario.objects.select_related(
            "paciente__user", "medico__user"
        ).all()
        if request.user.role == "medico":
            try:
                qs = qs.filter(medico=request.user.medico)
            except Exception:
                qs = qs.none()
        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)
        serializer = ProntuarioSerializer(qs, many=True)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Prontuários"], summary="Criar prontuário")
    def post(self, request):
        if request.user.role != "medico":
            return api_error("Apenas médicos podem criar prontuários.", http_status=403)
        serializer = ProntuarioSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(medico=request.user.medico)
            except Exception:
                return api_error("Perfil médico não encontrado.")
            return api_created(data=serializer.data, message="Prontuário criado com sucesso.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class ProntuarioDetailView(APIView):
    """GET/PATCH /api/prontuarios/<pk>/ — Detalhes e atualização de prontuário."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    def _get_prontuario(self, pk):
        try:
            return Prontuario.objects.select_related(
                "paciente__user", "medico__user"
            ).get(pk=pk)
        except Prontuario.DoesNotExist:
            return None

    @extend_schema(tags=["Prontuários"], summary="Detalhes do prontuário")
    def get(self, request, pk):
        prontuario = self._get_prontuario(pk)
        if not prontuario:
            return api_not_found("Prontuário não encontrado.")
        serializer = ProntuarioSerializer(prontuario)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Prontuários"], summary="Atualizar prontuário")
    def patch(self, request, pk):
        prontuario = self._get_prontuario(pk)
        if not prontuario:
            return api_not_found("Prontuário não encontrado.")
        if request.user.role == "medico":
            try:
                if prontuario.medico != request.user.medico:
                    return api_error("Você só pode editar seus próprios prontuários.", http_status=403)
            except Exception:
                return api_error("Perfil médico não encontrado.", http_status=403)
        serializer = ProntuarioSerializer(prontuario, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=serializer.data, message="Prontuário atualizado.")
        return api_error("Dados inválidos.", errors=serializer.errors)
