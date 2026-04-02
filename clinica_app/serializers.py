"""
clinica_app/serializers.py
Serializers do módulo Clínica e Secretaria.
"""
from rest_framework import serializers
from .models import Clinica, Secretaria


class ClinicaSerializer(serializers.ModelSerializer):
    nome_usuario = serializers.CharField(source="user.nome_completo", read_only=True)
    total_medicos = serializers.SerializerMethodField()

    class Meta:
        model = Clinica
        fields = [
            "id", "nome_usuario", "nome_fantasia", "razao_social",
            "cnpj", "telefone", "email_contato", "endereco",
            "horario_funcionamento", "logo", "medicos",
            "ativa", "total_medicos", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_total_medicos(self, obj):
        return obj.medicos.count()


class ClinicaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinica
        fields = [
            "nome_fantasia", "razao_social", "telefone",
            "email_contato", "endereco", "horario_funcionamento", "logo",
        ]


class SecretariaSerializer(serializers.ModelSerializer):
    nome_completo = serializers.CharField(source="user.nome_completo", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    clinica_nome = serializers.CharField(source="clinica.nome_fantasia", read_only=True)

    class Meta:
        model = Secretaria
        fields = [
            "id", "nome_completo", "email",
            "clinica", "clinica_nome", "cargo",
            "pode_agendar", "pode_ver_prontuario",
        ]
        read_only_fields = ["id"]
