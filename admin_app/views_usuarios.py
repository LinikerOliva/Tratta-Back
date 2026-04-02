"""
admin_app/views_usuarios.py
Views do painel admin para listagem e gestão de usuários.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.db.models import Q
from rest_framework import serializers

from trathea_core.utils.response import api_success, api_not_found
from trathea_core.auth.permissions import IsAdminUser
from core_app.models import CustomUser

class UsuarioAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "nome_completo", "email", "role", "is_active", "date_joined"]
        
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Frontend espera "nome" em vez de "nome_completo" (opcional, pode ser mapeado se precisar)
        ret["nome"] = ret.pop("nome_completo")
        return ret


class AdminUsuariosListView(APIView):
    """GET /api/admin-panel/usuarios/"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Listar todos os usuários")
    def get(self, request):
        qs = CustomUser.objects.all().order_by("-date_joined")
        search = request.query_params.get("search", "")
        if search:
            qs = qs.filter(Q(nome_completo__icontains=search) | Q(email__icontains=search))
            
        role = request.query_params.get("role", "")
        if role:
            qs = qs.filter(role=role)
            
        data = UsuarioAdminSerializer(qs, many=True).data
        return api_success(data=data)


class AdminUsuarioDetailView(APIView):
    """GET/PATCH/DELETE /api/admin-panel/usuarios/<pk>/"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Obter detalhes do usuário")
    def get(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
            data = UsuarioAdminSerializer(user).data
            return api_success(data=data)
        except CustomUser.DoesNotExist:
            return api_not_found("Usuário não encontrado.")

    @extend_schema(tags=["Admin"], summary="Editar usuário (nome, role, is_active, etc.)")
    def patch(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
            allowed_fields = ["nome_completo", "role", "is_active"]
            updated = []
            for field in allowed_fields:
                if field in request.data:
                    setattr(user, field, request.data[field])
                    updated.append(field)
            if updated:
                user.save(update_fields=updated)
            data = UsuarioAdminSerializer(user).data
            return api_success(data=data, message="Usuário atualizado com sucesso.")
        except CustomUser.DoesNotExist:
            return api_not_found("Usuário não encontrado.")

    @extend_schema(tags=["Admin"], summary="Desativar usuário")
    def delete(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
            user.is_active = False
            user.save(update_fields=["is_active"])
            return api_success(message="Usuário desativado com sucesso.")
        except CustomUser.DoesNotExist:
            return api_not_found("Usuário não encontrado.")
