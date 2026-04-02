"""
paciente_app/serializers.py
Serializers do módulo Paciente.
"""
from rest_framework import serializers
from .models import Paciente, Prontuario


class PacienteSerializer(serializers.ModelSerializer):
    nome_completo = serializers.CharField(source="user.nome_completo", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    idade = serializers.IntegerField(read_only=True)

    class Meta:
        model = Paciente
        fields = [
            "id", "nome_completo", "email", "idade",
            "data_nascimento", "tipo_sanguineo",
            "alergias", "medicamentos_uso_continuo",
            "convenio_nome", "convenio_numero",
            "medico_principal", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PacienteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = [
            "tipo_sanguineo", "alergias", "medicamentos_uso_continuo",
            "convenio_nome", "convenio_numero", "medico_principal",
        ]


class ProntuarioSerializer(serializers.ModelSerializer):
    paciente_nome = serializers.CharField(source="paciente.user.nome_completo", read_only=True)
    medico_nome = serializers.CharField(source="medico.user.nome_completo", read_only=True)
    medico_crm = serializers.CharField(source="medico.crm", read_only=True)

    class Meta:
        model = Prontuario
        fields = [
            "id", "paciente", "paciente_nome",
            "medico", "medico_nome", "medico_crm",
            "data_consulta", "queixa_principal", "anamnese",
            "exame_fisico", "hipotese_diagnostica",
            "diagnostico_cid10", "conduta", "retorno_em",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "medico", "created_at", "updated_at"]
