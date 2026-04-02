"""
exame_app/views.py
Views do módulo Exames.
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error, api_not_found, api_created
from trathea_core.auth.permissions import IsDoctor, IsMedicalStaff

from .models import TipoExame, SolicitacaoExame
from .serializers import (
    TipoExameSerializer, SolicitacaoExameSerializer, SolicitacaoExameCreateSerializer,
)

logger = logging.getLogger("trathea")


class TipoExameListView(APIView):
    """GET /api/exames/tipos/ — Catálogo de tipos de exame."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Exames"], summary="Listar tipos de exame")
    def get(self, request):
        nome = request.query_params.get("nome")
        qs = TipoExame.objects.all()
        if nome:
            qs = qs.filter(nome__icontains=nome)
        serializer = TipoExameSerializer(qs, many=True)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Exames"], summary="Criar tipo de exame")
    def post(self, request):
        if request.user.role != "admin":
            return api_error("Apenas admins podem cadastrar tipos de exame.", http_status=403)
        serializer = TipoExameSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_created(data=serializer.data, message="Tipo de exame cadastrado.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class SolicitacaoExameListView(APIView):
    """GET/POST /api/exames/ — Lista e cria solicitações de exame."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    @extend_schema(tags=["Exames"], summary="Listar solicitações de exame")
    def get(self, request):
        qs = SolicitacaoExame.objects.select_related(
            "paciente__user", "medico__user", "tipo_exame"
        ).all()
        if request.user.role == "medico":
            try:
                qs = qs.filter(medico=request.user.medico)
            except Exception:
                qs = qs.none()
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        urgente = request.query_params.get("urgente")
        if urgente is not None:
            qs = qs.filter(urgente=urgente.lower() == "true")
        serializer = SolicitacaoExameSerializer(qs, many=True)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Exames"], summary="Solicitar exame")
    def post(self, request):
        if request.user.role != "medico":
            return api_error("Apenas médicos podem solicitar exames.", http_status=403)
        serializer = SolicitacaoExameCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                exame = serializer.save(medico=request.user.medico)
            except Exception:
                return api_error("Perfil médico não encontrado.")
            return api_created(
                data=SolicitacaoExameSerializer(exame).data,
                message="Exame solicitado com sucesso.",
            )
        return api_error("Dados inválidos.", errors=serializer.errors)


class SolicitacaoExameDetailView(APIView):
    """GET/PATCH /api/exames/<pk>/ — Detalhes e atualização de exame."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    def _get_exame(self, pk):
        try:
            return SolicitacaoExame.objects.select_related(
                "paciente__user", "medico__user", "tipo_exame"
            ).get(pk=pk)
        except SolicitacaoExame.DoesNotExist:
            return None

    @extend_schema(tags=["Exames"], summary="Detalhes da solicitação de exame")
    def get(self, request, pk):
        exame = self._get_exame(pk)
        if not exame:
            return api_not_found("Solicitação de exame não encontrada.")
        serializer = SolicitacaoExameSerializer(exame)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Exames"], summary="Atualizar resultado do exame")
    def patch(self, request, pk):
        exame = self._get_exame(pk)
        if not exame:
            return api_not_found("Solicitação de exame não encontrada.")
        serializer = SolicitacaoExameSerializer(exame, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=serializer.data, message="Exame atualizado.")
        return api_error("Dados inválidos.", errors=serializer.errors)
