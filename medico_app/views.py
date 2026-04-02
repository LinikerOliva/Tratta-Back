"""
medico_app/views.py
Views do módulo Médico.
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from trathea_core.utils.response import api_success, api_error, api_not_found, api_created
from trathea_core.auth.permissions import IsDoctor, IsAdminUser, IsMedicalStaff, IsDoctorOrAdmin

from .models import Medico, Disponibilidade
from .serializers import (
    MedicoSerializer, MedicoUpdateSerializer,
    MedicoPublicoSerializer, DisponibilidadeSerializer,
)

logger = logging.getLogger("trathea")


class MedicoListView(APIView):
    """GET /api/doctors/ — Lista médicos (acesso: equipe médica e admin)."""

    permission_classes = [IsAuthenticated, IsMedicalStaff]

    @extend_schema(tags=["Médicos"], summary="Listar médicos")
    def get(self, request):
        especialidade = request.query_params.get("especialidade")
        qs = Medico.objects.select_related("user", "clinica_principal").all()
        if especialidade:
            qs = qs.filter(especialidade__icontains=especialidade)
        serializer = MedicoPublicoSerializer(qs, many=True)
        return api_success(data=serializer.data)


class MedicoDetailView(APIView):
    """GET/PATCH /api/doctors/<pk>/ — Detalhes e atualização do médico."""

    permission_classes = [IsAuthenticated]

    def _get_medico(self, pk):
        try:
            return Medico.objects.select_related("user", "clinica_principal").get(pk=pk)
        except Medico.DoesNotExist:
            return None

    @extend_schema(tags=["Médicos"], summary="Detalhe do médico")
    def get(self, request, pk):
        medico = self._get_medico(pk)
        if not medico:
            return api_not_found("Médico não encontrado.")
        serializer = MedicoSerializer(medico)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Médicos"], summary="Atualizar perfil do médico")
    def patch(self, request, pk):
        medico = self._get_medico(pk)
        if not medico:
            return api_not_found("Médico não encontrado.")
        if medico.user != request.user and request.user.role != "admin":
            return api_error("Você só pode editar seu próprio perfil.", http_status=403)
        serializer = MedicoUpdateSerializer(medico, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=MedicoSerializer(medico).data, message="Perfil atualizado.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class MeuPerfilMedicoView(APIView):
    """GET/PATCH /api/doctors/me/ — O médico acessa seu próprio perfil."""

    permission_classes = [IsAuthenticated, IsDoctor]

    @extend_schema(tags=["Médicos"], summary="Meu perfil médico")
    def get(self, request):
        try:
            medico = request.user.medico
        except Medico.DoesNotExist:
            return api_not_found("Perfil médico não encontrado para este usuário.")
        return api_success(data=MedicoSerializer(medico).data)

    @extend_schema(tags=["Médicos"], summary="Atualizar meu perfil médico")
    def patch(self, request):
        try:
            medico = request.user.medico
        except Medico.DoesNotExist:
            return api_not_found("Perfil médico não encontrado.")
        serializer = MedicoUpdateSerializer(medico, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_success(data=MedicoSerializer(medico).data, message="Perfil atualizado com sucesso.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class MedicoDisponibilidadeView(APIView):
    """GET/POST /api/doctors/<pk>/agenda/ — Agenda do médico."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Médicos"], summary="Ver disponibilidade do médico")
    def get(self, request, pk):
        try:
            medico = Medico.objects.get(pk=pk)
        except Medico.DoesNotExist:
            return api_not_found("Médico não encontrado.")
        disponibilidades = medico.disponibilidades.filter(ativo=True)
        serializer = DisponibilidadeSerializer(disponibilidades, many=True)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Médicos"], summary="Adicionar disponibilidade")
    def post(self, request, pk):
        try:
            medico = Medico.objects.get(pk=pk)
        except Medico.DoesNotExist:
            return api_not_found("Médico não encontrado.")
        if medico.user != request.user:
            return api_error("Você só pode gerenciar sua própria agenda.", http_status=403)
        serializer = DisponibilidadeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(medico=medico)
            return api_created(data=serializer.data, message="Disponibilidade adicionada.")
        return api_error("Dados inválidos.", errors=serializer.errors)


class MeusPacientesView(APIView):
    """GET /api/doctors/me/pacientes/ — Pacientes que o médico já atendeu."""

    permission_classes = [IsAuthenticated, IsDoctorOrAdmin]

    @extend_schema(tags=["Médicos"], summary="Listar meus pacientes (baseado em consultas)")
    def get(self, request):
        from consulta_app.models import Consulta
        from django.db.models import Count, Max, Q

        # Admin vê todas as consultas; médico vê só as dele
        if request.user.role == "admin":
            consultas_filter = {}
        else:
            try:
                medico = request.user.medico
                consultas_filter = {"medico": medico}
            except Medico.DoesNotExist:
                return api_not_found("Perfil médico não encontrado.")

        # Buscar pacientes únicos que tiveram consultas com este médico
        pacientes_qs = (
            Consulta.objects
            .filter(**consultas_filter)
            .values("paciente")
            .annotate(
                total_consultas=Count("id"),
                ultima_consulta=Max("data_inicio"),
            )
            .order_by("-ultima_consulta")
        )

        # Filtro de busca por nome ou email
        search = request.query_params.get("search", "").strip()
        if search:
            pacientes_qs = pacientes_qs.filter(
                Q(paciente__user__nome_completo__icontains=search) |
                Q(paciente__user__email__icontains=search)
            )

        # Filtro por contagem mínima de consultas
        min_consultas = request.query_params.get("min_consultas")
        if min_consultas:
            try:
                pacientes_qs = pacientes_qs.filter(total_consultas__gte=int(min_consultas))
            except ValueError:
                pass

        # Ordenação
        ordem = request.query_params.get("ordem", "recente")
        if ordem == "mais_consultas":
            pacientes_qs = pacientes_qs.order_by("-total_consultas")
        elif ordem == "menos_consultas":
            pacientes_qs = pacientes_qs.order_by("total_consultas")
        elif ordem == "nome":
            pacientes_qs = pacientes_qs.order_by("paciente__user__nome_completo")
        # default: mais recente

        # Montar resposta
        from paciente_app.models import Paciente
        result = []
        for item in pacientes_qs:
            try:
                pac = Paciente.objects.select_related("user").get(pk=item["paciente"])
                result.append({
                    "id": pac.id,
                    "user_id": pac.user_id,
                    "nome": pac.user.nome_completo,
                    "email": pac.user.email,
                    "data_nascimento": str(pac.data_nascimento) if pac.data_nascimento else None,
                    "tipo_sanguineo": getattr(pac, "tipo_sanguineo", ""),
                    "alergias": getattr(pac, "alergias", ""),
                    "total_consultas": item["total_consultas"],
                    "ultima_consulta": item["ultima_consulta"].isoformat() if item["ultima_consulta"] else None,
                })
            except Paciente.DoesNotExist:
                continue

        return api_success(data=result)
