"""
admin_app/views_planos.py
Views para o gerenciamento de planos de assinatura pelo Admin.
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from trathea_core.auth.permissions import IsAdminUser
from medico_app.models_plano import Plano
from medico_app.serializers_plano import PlanoSerializer

class AdminPlanosListView(generics.ListCreateAPIView):
    """
    GET: Lista todos os planos (incluindo inativos).
    POST: Cria um novo plano.
    """
    queryset = Plano.objects.all().order_by("preco_mensal")
    serializer_class = PlanoSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class AdminPlanosDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retorna os detalhes de um plano.
    PUT/PATCH: Atualiza os dados de um plano.
    DELETE: Remove um plano (pode ser hard delete ou soft delete ajustando o serializer).
    """
    queryset = Plano.objects.all()
    serializer_class = PlanoSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
