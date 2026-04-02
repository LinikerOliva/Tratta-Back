"""
consulta_app/views.py
Views do módulo Consulta e Agendamento.
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.utils import timezone

from trathea_core.utils.response import api_success, api_error, api_not_found, api_created
from trathea_core.auth.permissions import IsDoctor, IsMedicalStaff

from .models import Agendamento, Consulta
from .serializers import (
    AgendamentoSerializer, AgendamentoCreateSerializer,
    ConsultaSerializer, ConsultaCreateSerializer,
)

logger = logging.getLogger("trathea")


# ── Agendamentos ──────────────────────────────────────────────────────────────

class AgendamentoListView(APIView):
    """GET/POST /api/agendamentos/ — Lista e cria agendamentos."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Agendamentos"], summary="Listar agendamentos")
    def get(self, request):
        qs = Agendamento.objects.select_related(
            "paciente__user", "medico__user", "clinica"
        ).all()
        role = request.user.role
        if role == "medico":
            try:
                qs = qs.filter(medico=request.user.medico)
            except Exception:
                qs = qs.none()
        elif role == "paciente":
            try:
                qs = qs.filter(paciente=request.user.paciente)
            except Exception:
                qs = qs.none()
        elif role == "clinica":
            try:
                qs = qs.filter(clinica=request.user.clinica)
            except Exception:
                qs = qs.none()
        # secretaria e admin vêem todos
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        serializer = AgendamentoSerializer(qs, many=True)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Agendamentos"], summary="Criar agendamento")
    def post(self, request):
        serializer = AgendamentoCreateSerializer(data=request.data)
        if serializer.is_valid():
            agendamento = serializer.save(criado_por=request.user)
            return api_created(
                data=AgendamentoSerializer(agendamento).data,
                message="Agendamento criado com sucesso.",
            )
        return api_error("Dados inválidos.", errors=serializer.errors)


class AgendamentoDetailView(APIView):
    """GET/PATCH /api/agendamentos/<pk>/ — Detalhes e atualização de agendamento."""

    permission_classes = [IsAuthenticated]

    def _get_agendamento(self, pk):
        try:
            return Agendamento.objects.select_related(
                "paciente__user", "medico__user", "clinica"
            ).get(pk=pk)
        except Agendamento.DoesNotExist:
            return None

    @extend_schema(tags=["Agendamentos"], summary="Detalhes do agendamento")
    def get(self, request, pk):
        agendamento = self._get_agendamento(pk)
        if not agendamento:
            return api_not_found("Agendamento não encontrado.")
        serializer = AgendamentoSerializer(agendamento)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Agendamentos"], summary="Atualizar status do agendamento")
    def patch(self, request, pk):
        agendamento = self._get_agendamento(pk)
        if not agendamento:
            return api_not_found("Agendamento não encontrado.")
        serializer = AgendamentoSerializer(agendamento, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=serializer.data, message="Agendamento atualizado.")
        return api_error("Dados inválidos.", errors=serializer.errors)


# ── Consultas ─────────────────────────────────────────────────────────────────

class ConsultaListView(APIView):
    """GET/POST /api/consultas/ — Lista e inicia consultas."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    @extend_schema(tags=["Consultas"], summary="Listar consultas")
    def get(self, request):
        qs = Consulta.objects.select_related(
            "paciente__user", "medico__user", "agendamento"
        ).all()
        if request.user.role == "medico":
            try:
                qs = qs.filter(medico=request.user.medico)
            except Exception:
                qs = qs.none()
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        serializer = ConsultaSerializer(qs, many=True)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Consultas"], summary="Iniciar consulta")
    def post(self, request):
        if request.user.role != "medico":
            return api_error("Apenas médicos podem iniciar consultas.", http_status=403)
        serializer = ConsultaCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                consulta = serializer.save(medico=request.user.medico)
            except Exception:
                return api_error("Perfil médico não encontrado.")
            return api_created(
                data=ConsultaSerializer(consulta).data,
                message="Consulta iniciada.",
            )
        return api_error("Dados inválidos.", errors=serializer.errors)


class ConsultaDetailView(APIView):
    """GET/PATCH /api/consultas/<pk>/ — Detalhes e finalização de consulta."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    def _get_consulta(self, pk):
        try:
            return Consulta.objects.select_related(
                "paciente__user", "medico__user"
            ).get(pk=pk)
        except Consulta.DoesNotExist:
            return None

    @extend_schema(tags=["Consultas"], summary="Detalhes da consulta")
    def get(self, request, pk):
        consulta = self._get_consulta(pk)
        if not consulta:
            return api_not_found("Consulta não encontrada.")
        serializer = ConsultaSerializer(consulta)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Consultas"], summary="Atualizar/finalizar consulta")
    def patch(self, request, pk):
        consulta = self._get_consulta(pk)
        if not consulta:
            return api_not_found("Consulta não encontrada.")
        # Finalizar automaticamente se status=finalizada
        data = request.data.copy()
        if data.get("status") == "finalizada" and not consulta.data_fim:
            data["data_fim"] = timezone.now().isoformat()
        serializer = ConsultaSerializer(consulta, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=serializer.data, message="Consulta atualizada.")
        return api_error("Dados inválidos.", errors=serializer.errors)
