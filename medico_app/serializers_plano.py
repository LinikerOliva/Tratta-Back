"""
medico_app/serializers_plano.py
Serializers para o sistema de planos de assinatura.

O React consome esses dados para:
- Exibir o plano ativo e limites no painel do médico.
- Bloquear/liberar botões de IA e Assinatura via feature flags.
- Mostrar barra de progresso de consumo mensal.
"""
from rest_framework import serializers
from .models_plano import Plano, AssinaturaMedico


class PlanoSerializer(serializers.ModelSerializer):
    """Serializa os dados do catálogo de planos (para listagem/comparação)."""

    transcricoes_ilimitadas = serializers.BooleanField(read_only=True)
    assinaturas_ilimitadas = serializers.BooleanField(read_only=True)

    class Meta:
        model = Plano
        fields = [
            "id", "nome", "tipo", "descricao", "preco_mensal",
            "preco_promocional",
            "limite_transcricoes", "limite_assinaturas",
            "transcricoes_ilimitadas", "assinaturas_ilimitadas",
            "tem_dashboard_avancado", "tem_suporte_prioritario",
            "tem_multi_usuarios", "tem_relatorios_faturamento",
        ]


class AssinaturaMedicoSerializer(serializers.ModelSerializer):
    """
    Serializa o status da assinatura do médico logado.

    Campos derivados:
    - pode_transcrever: bool → React habilita/desabilita botão de IA.
    - pode_assinar: bool → React habilita/desabilita botão de assinatura.
    - transcricoes_restantes: int|null → null = ilimitado.
    - assinaturas_restantes: int|null → null = ilimitado.
    - percentual_transcricoes: float → Para barra de progresso (0.0 a 1.0).
    - percentual_assinaturas: float → Para barra de progresso (0.0 a 1.0).
    """

    plano = PlanoSerializer(read_only=True)

    # ── Campos computados para o frontend ────────────────────────────────
    pode_transcrever = serializers.SerializerMethodField()
    pode_assinar = serializers.SerializerMethodField()
    transcricoes_restantes = serializers.SerializerMethodField()
    assinaturas_restantes = serializers.SerializerMethodField()
    percentual_transcricoes = serializers.SerializerMethodField()
    percentual_assinaturas = serializers.SerializerMethodField()

    class Meta:
        model = AssinaturaMedico
        fields = [
            "id", "plano", "status",
            "transcricoes_usadas", "assinaturas_usadas",
            "ciclo_inicio", "ciclo_fim",
            # Campos computados
            "pode_transcrever", "pode_assinar",
            "transcricoes_restantes", "assinaturas_restantes",
            "percentual_transcricoes", "percentual_assinaturas",
        ]

    def get_pode_transcrever(self, obj) -> bool:
        return obj.pode_transcrever()

    def get_pode_assinar(self, obj) -> bool:
        return obj.pode_assinar_govbr()

    def get_transcricoes_restantes(self, obj) -> int | None:
        return obj.transcricoes_restantes

    def get_assinaturas_restantes(self, obj) -> int | None:
        return obj.assinaturas_restantes

    def get_percentual_transcricoes(self, obj) -> float:
        """Retorna 0.0 a 1.0. Para ilimitado retorna 0.0."""
        if obj.plano.transcricoes_ilimitadas:
            return 0.0
        if obj.plano.limite_transcricoes == 0:
            return 0.0
        return round(obj.transcricoes_usadas / obj.plano.limite_transcricoes, 2)

    def get_percentual_assinaturas(self, obj) -> float:
        """Retorna 0.0 a 1.0. Para ilimitado retorna 0.0."""
        if obj.plano.assinaturas_ilimitadas:
            return 0.0
        if obj.plano.limite_assinaturas == 0:
            return 0.0
        return round(obj.assinaturas_usadas / obj.plano.limite_assinaturas, 2)


class MeuPlanoResumoSerializer(serializers.Serializer):
    """
    Serializer simplificado para embed no MedicoSerializer.
    O frontend recebe isso junto com GET /api/doctors/me/ para
    saber rapidamente o que está liberado.
    """

    plano_nome = serializers.CharField()
    plano_tipo = serializers.CharField()
    status = serializers.CharField()
    pode_transcrever = serializers.BooleanField()
    pode_assinar = serializers.BooleanField()
    transcricoes_restantes = serializers.IntegerField(allow_null=True)
    assinaturas_restantes = serializers.IntegerField(allow_null=True)
    tem_dashboard_avancado = serializers.BooleanField()
    percentual_transcricoes = serializers.FloatField()
    percentual_assinaturas = serializers.FloatField()
