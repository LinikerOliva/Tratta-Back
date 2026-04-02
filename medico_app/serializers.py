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

    class Meta:
        model = Medico
        fields = [
            "id", "nome_completo", "email",
            "crm", "crm_estado", "especialidade", "sub_especialidades",
            "bio", "atende_convenio", "is_govbr_linked",
            "clinica_principal", "disponibilidades",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_govbr_linked", "created_at", "updated_at"]


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
