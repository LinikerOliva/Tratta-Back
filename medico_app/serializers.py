"""
medico_app/serializers.py
Serializers do módulo Médico.
"""
from rest_framework import serializers
from .models import Medico, Disponibilidade


class DisponibilidadeSerializer(serializers.ModelSerializer):
    dia_semana_display = serializers.CharField(source="get_dia_semana_display", read_only=True)

    class Meta:
        model = Disponibilidade
        fields = [
            "id", "dia_semana", "dia_semana_display",
            "hora_inicio", "hora_fim", "duracao_consulta_min", "ativo",
        ]


class MedicoSerializer(serializers.ModelSerializer):
    nome_completo = serializers.CharField(source="user.nome_completo", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    disponibilidades = DisponibilidadeSerializer(many=True, read_only=True)
    plano_resumo = serializers.SerializerMethodField()

    class Meta:
        model = Medico
        fields = [
            "id", "nome_completo", "email",
            "crm", "crm_estado", "especialidade", "sub_especialidades",
            "bio", "atende_convenio", "is_govbr_linked",
            "clinica_principal", "disponibilidades",
            "plano_resumo",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_govbr_linked", "created_at", "updated_at"]

    def get_plano_resumo(self, obj) -> dict | None:
        """Retorna resumo do plano ativo para o frontend decidir feature gates."""
        assinatura = getattr(obj, "assinatura", None)
        if not assinatura:
            return None
        return {
            "plano_nome": assinatura.plano.nome,
            "plano_tipo": assinatura.plano.tipo,
            "status": assinatura.status,
            "pode_transcrever": assinatura.pode_transcrever(),
            "pode_assinar": assinatura.pode_assinar_govbr(),
            "transcricoes_restantes": assinatura.transcricoes_restantes,
            "assinaturas_restantes": assinatura.assinaturas_restantes,
            "tem_dashboard_avancado": assinatura.plano.tem_dashboard_avancado,
            "percentual_transcricoes": (
                round(assinatura.transcricoes_usadas / assinatura.plano.limite_transcricoes, 2)
                if not assinatura.plano.transcricoes_ilimitadas and assinatura.plano.limite_transcricoes > 0
                else 0.0
            ),
            "percentual_assinaturas": (
                round(assinatura.assinaturas_usadas / assinatura.plano.limite_assinaturas, 2)
                if not assinatura.plano.assinaturas_ilimitadas and assinatura.plano.limite_assinaturas > 0
                else 0.0
            ),
        }


class MedicoUpdateSerializer(serializers.ModelSerializer):
    """Serializer para o médico atualizar seu próprio perfil."""

    class Meta:
        model = Medico
        fields = [
            "especialidade", "sub_especialidades", "bio",
            "atende_convenio", "clinica_principal", "assinatura_img",
        ]


class MedicoPublicoSerializer(serializers.ModelSerializer):
    """Serializer com dados públicos do médico (para pacientes buscarem)."""
    nome_completo = serializers.CharField(source="user.nome_completo", read_only=True)

    class Meta:
        model = Medico
        fields = [
            "id", "nome_completo", "crm", "crm_estado",
            "especialidade", "sub_especialidades", "bio",
            "atende_convenio",
        ]
