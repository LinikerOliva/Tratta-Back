"""
admin_app/serializers.py
Serializers do módulo Admin.
"""
from rest_framework import serializers
from .models import SolicitacaoCadastro


class SolicitacaoCadastroSerializer(serializers.ModelSerializer):
    solicitante_email = serializers.EmailField(source="solicitante.email", read_only=True)
    solicitante_nome = serializers.CharField(source="solicitante.nome_completo", read_only=True)
    avaliado_por_email = serializers.EmailField(source="avaliado_por.email", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SolicitacaoCadastro
        fields = [
            "id", "solicitante", "solicitante_email", "solicitante_nome",
            "tipo", "tipo_display", "status", "status_display",
            "dados_adicionais", "documento_comprobatorio",
            "avaliado_por", "avaliado_por_email",
            "motivo_rejeicao", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "solicitante", "avaliado_por",
            "created_at", "updated_at",
        ]


class SolicitacaoCadastroCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitacaoCadastro
        fields = ["tipo", "dados_adicionais", "documento_comprobatorio"]


class AvaliarSolicitacaoSerializer(serializers.Serializer):
    """Serializer para o admin aprovar ou rejeitar uma solicitação."""
    status = serializers.ChoiceField(choices=["aprovada", "rejeitada"])
    motivo_rejeicao = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["status"] == "rejeitada" and not attrs.get("motivo_rejeicao"):
            raise serializers.ValidationError(
                {"motivo_rejeicao": "Informe o motivo da rejeição."}
            )
        return attrs
