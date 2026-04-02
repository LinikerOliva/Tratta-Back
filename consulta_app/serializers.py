"""
consulta_app/serializers.py
Serializers do módulo Consulta e Agendamento.
"""
from rest_framework import serializers
from .models import Agendamento, Consulta


class AgendamentoSerializer(serializers.ModelSerializer):
    paciente_nome = serializers.CharField(source="paciente.user.nome_completo", read_only=True)
    medico_nome = serializers.CharField(source="medico.user.nome_completo", read_only=True)
    medico_crm = serializers.CharField(source="medico.crm", read_only=True)
    clinica_nome = serializers.CharField(source="clinica.nome_fantasia", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Agendamento
        fields = [
            "id", "paciente", "paciente_nome",
            "medico", "medico_nome", "medico_crm",
            "clinica", "clinica_nome",
            "data_hora", "motivo", "status", "status_display",
            "observacoes_paciente", "criado_por", "created_at",
        ]
        read_only_fields = ["id", "criado_por", "created_at"]


class AgendamentoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agendamento
        fields = [
            "paciente", "medico", "clinica",
            "data_hora", "motivo", "observacoes_paciente",
        ]


class ConsultaSerializer(serializers.ModelSerializer):
    paciente_nome = serializers.CharField(source="paciente.user.nome_completo", read_only=True)
    medico_nome = serializers.CharField(source="medico.user.nome_completo", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Consulta
        fields = [
            "id", "agendamento",
            "paciente", "paciente_nome",
            "medico", "medico_nome",
            "data_inicio", "data_fim",
            "status", "status_display", "resumo",
            "transcricao_texto", "queixa_principal",
            "anamnese", "hipotese_diagnostica",
            "duracao_segundos", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ConsultaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consulta
        fields = ["agendamento", "paciente", "medico", "data_inicio", "resumo"]
