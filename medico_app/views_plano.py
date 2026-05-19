"""
medico_app/views_plano.py
Views/endpoints para o sistema de planos de assinatura.

Endpoints:
- GET /api/doctors/me/plano/  → Status do plano do médico logado
- GET /api/planos/            → Catálogo de planos disponíveis
"""
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error, api_not_found
from trathea_core.auth.permissions import IsDoctor

from .models_plano import Plano, AssinaturaMedico
from .serializers_plano import (
    PlanoSerializer,
    AssinaturaMedicoSerializer,
)

logger = logging.getLogger("trathea")


@extend_schema(
    tags=["Planos"],
    summary="Meu plano atual",
    description=(
        "Retorna o plano ativo do médico logado com status de consumo. "
        "O frontend usa esses dados para bloquear/liberar funcionalidades."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsDoctor])
def meu_plano_view(request):
    """GET /api/doctors/me/plano/ — Plano do médico logado."""
    medico = getattr(request.user, "medico", None)
    if not medico:
        return api_not_found("Perfil médico não encontrado.")

    try:
        assinatura = medico.assinatura
    except AssinaturaMedico.DoesNotExist:
        return api_error(
            "Nenhum plano vinculado. Entre em contato com o suporte.",
            http_status=404,
        )

    serializer = AssinaturaMedicoSerializer(assinatura)
    return api_success(data=serializer.data)


@extend_schema(
    tags=["Planos"],
    summary="Catálogo de planos",
    description="Lista todos os planos ativos disponíveis para contratação.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalogo_planos_view(request):
    """GET /api/planos/ — Lista planos disponíveis."""
    planos = Plano.objects.filter(ativo=True)
    serializer = PlanoSerializer(planos, many=True)
    return api_success(data=serializer.data)
