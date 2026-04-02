"""
admin_app/views_clinicas.py
Views do painel admin para listagem e gestão de clínicas.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.db.models import Q
from rest_framework import serializers

from trathea_core.utils.response import api_success, api_not_found
from trathea_core.auth.permissions import IsAdminUser
from clinica_app.models import Clinica

class ClinicaAdminSerializer(serializers.ModelSerializer):
    email_contato = serializers.EmailField(default="")
    
    class Meta:
        model = Clinica
        fields = ["id", "nome_fantasia", "razao_social", "cnpj", "email_contato", "telefone", "ativa", "created_at"]
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Fallback de email pro admin dashboard se a clinica n tem, tenta do CustomUser
        if not ret.get("email_contato") and instance.user:
            ret["email"] = instance.user.email
        else:
            ret["email"] = ret.pop("email_contato", "")
        ret["nome"] = ret.pop("nome_fantasia", "")
        return ret


class AdminClinicasListView(APIView):
    """GET /api/admin-panel/clinicas/"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Listar todas as clínicas")
    def get(self, request):
        qs = Clinica.objects.select_related("user").all().order_by("-created_at")
        search = request.query_params.get("search", "")
        if search:
            qs = qs.filter(Q(nome_fantasia__icontains=search) | Q(cnpj__icontains=search) | Q(razao_social__icontains=search))
            
        data = ClinicaAdminSerializer(qs, many=True).data
        return api_success(data=data)


class AdminClinicaDetailView(APIView):
    """GET/PATCH /api/admin-panel/clinicas/<pk>/"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @extend_schema(tags=["Admin"], summary="Detalhes da clínica")
    def get(self, request, pk):
        try:
            clinica = Clinica.objects.get(pk=pk)
            return api_success(data=ClinicaAdminSerializer(clinica).data)
        except Clinica.DoesNotExist:
            return api_not_found("Clínica não encontrada.")
            
    @extend_schema(tags=["Admin"], summary="Atualizar clínica")
    def patch(self, request, pk):
        try:
            clinica = Clinica.objects.get(pk=pk)
            ativa = request.data.get("ativa")
            if ativa is not None:
                clinica.ativa = ativa
                clinica.save(update_fields=["ativa"])
            return api_success(data=ClinicaAdminSerializer(clinica).data, message="Clínica atualizada.")
        except Clinica.DoesNotExist:
            return api_not_found("Clínica não encontrada.")
