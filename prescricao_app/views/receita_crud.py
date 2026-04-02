"""
prescricao_app/views/receita_crud.py
CRUD de receitas médicas — criar, listar, detalhar, editar, deletar.
Lógica de negócio fica em services/. Views são apenas orquestradores HTTP.
"""
import logging

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from trathea_core.utils.response import api_success, api_created, api_error, api_not_found
from trathea_core.auth.permissions import IsDoctor, IsDoctorOrAdmin, CanAccessPatientData
from trathea_core.utils.pagination import TratheaPagination

from prescricao_app.models import Receita
from prescricao_app.serializers import ReceitaSerializer, ReceitaCreateSerializer

logger = logging.getLogger("trathea")


class ReceitaListCreateView(APIView):
    """
    GET  /api/receitas/  — Lista receitas (médico vê as próprias, admin vê todas)
    POST /api/receitas/  — Cria nova receita (médico only)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsDoctor()]
        return [IsAuthenticated(), IsDoctorOrAdmin()]

    @extend_schema(
        tags=["Receitas"],
        summary="Listar receitas",
        description="Médico lista suas receitas. Admin lista todas.",
        parameters=[
            OpenApiParameter("status", description="Filtrar por status", required=False),
            OpenApiParameter("paciente_id", description="Filtrar por paciente", required=False),
            OpenApiParameter("tipo", description="Filtrar por tipo", required=False),
        ],
        responses={200: OpenApiResponse(description="Lista paginada de receitas.")},
    )
    def get(self, request):
        user = request.user
        queryset = Receita.objects.select_related(
            "medico__user", "paciente__user", "consulta"
        ).prefetch_related("itens__medicamento")

        # RBAC: médico vê apenas as suas receitas
        if user.role == "medico":
            queryset = queryset.filter(medico__user=user)
        elif user.role not in ("admin",):
            return api_error("Acesso negado.", http_status=403)

        # Filtros opcionais
        if status := request.GET.get("status"):
            queryset = queryset.filter(status=status)
        if paciente_id := request.GET.get("paciente_id"):
            queryset = queryset.filter(paciente_id=paciente_id)
        if tipo := request.GET.get("tipo"):
            queryset = queryset.filter(tipo=tipo)

        paginator = TratheaPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ReceitaSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Receitas"],
        summary="Criar receita",
        description="Cria uma nova receita médica (status inicial: rascunho).",
        responses={
            201: OpenApiResponse(description="Receita criada."),
            400: OpenApiResponse(description="Dados inválidos."),
            403: OpenApiResponse(description="Apenas médicos podem criar receitas."),
        },
    )
    def post(self, request):
        serializer = ReceitaCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return api_error(
                message="Dados inválidos. Verifique os campos.",
                errors=serializer.errors,
            )

        receita = serializer.save()
        return api_created(
            data=ReceitaSerializer(receita).data,
            message="Receita criada com sucesso.",
        )


class ReceitaDetailView(APIView):
    """
    GET    /api/receitas/{id}/  — Detalhe
    PUT    /api/receitas/{id}/  — Editar (apenas status=rascunho)
    DELETE /api/receitas/{id}/  — Deletar (apenas status=rascunho)
    """

    permission_classes = [IsAuthenticated]

    def _get_receita(self, pk, user):
        """Busca receita com verificação de acesso RBAC."""
        try:
            receita = Receita.objects.select_related(
                "medico__user", "paciente__user"
            ).prefetch_related("itens__medicamento").get(pk=pk)
        except Receita.DoesNotExist:
            return None, api_not_found("Receita não encontrada.")

        # RBAC: médico só acessa as próprias; paciente só acessa as suas
        if user.role == "medico" and receita.medico.user != user:
            return None, api_error("Você não tem acesso a esta receita.", http_status=403)
        if user.role == "paciente" and receita.paciente.user != user:
            return None, api_error("Você não tem acesso a esta receita.", http_status=403)
        if user.role not in ("medico", "paciente", "admin"):
            return None, api_error("Acesso negado.", http_status=403)

        return receita, None

    @extend_schema(tags=["Receitas"], summary="Detalhe de receita")
    def get(self, request, pk):
        receita, error = self._get_receita(pk, request.user)
        if error:
            return error
        return api_success(data=ReceitaSerializer(receita).data)

    @extend_schema(tags=["Receitas"], summary="Editar receita (apenas rascunho)")
    def put(self, request, pk):
        if request.user.role != "medico":
            return api_error("Apenas médicos podem editar receitas.", http_status=403)

        receita, error = self._get_receita(pk, request.user)
        if error:
            return error

        if not receita.pode_ser_editada:
            return api_error(
                f"Receita com status '{receita.status}' não pode ser editada. "
                "Apenas receitas em rascunho podem ser modificadas."
            )

        serializer = ReceitaCreateSerializer(
            receita, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return api_error("Dados inválidos.", errors=serializer.errors)

        receita_atualizada = serializer.save()
        return api_success(
            data=ReceitaSerializer(receita_atualizada).data,
            message="Receita atualizada com sucesso.",
        )

    @extend_schema(tags=["Receitas"], summary="Deletar receita (apenas rascunho)")
    def delete(self, request, pk):
        if request.user.role not in ("medico", "admin"):
            return api_error("Acesso negado.", http_status=403)

        receita, error = self._get_receita(pk, request.user)
        if error:
            return error

        if not receita.pode_ser_editada:
            return api_error(
                f"Receita com status '{receita.status}' não pode ser excluída."
            )

        receita.delete()
        return api_success(message="Receita excluída com sucesso.")
