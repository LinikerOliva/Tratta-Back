"""
exame_app/serializers.py
Serializers do módulo Exames.
"""
from rest_framework import serializers
from .models import TipoExame, SolicitacaoExame


class TipoExameSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoExame
        fields = [
            "id", "nome", "descricao", "codigo_cbhpm",
            "requer_jejum", "instrucoes_preparo",
        ]


class SolicitacaoExameSerializer(serializers.ModelSerializer):
    tipo_exame_nome = serializers.CharField(source="tipo_exame.nome", read_only=True)
    paciente_nome = serializers.CharField(source="paciente.user.nome_completo", read_only=True)
    medico_nome = serializers.CharField(source="medico.user.nome_completo", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SolicitacaoExame
        fields = [
            "id", "consulta",
            "paciente", "paciente_nome",
            "medico", "medico_nome",
            "tipo_exame", "tipo_exame_nome",
            "status", "status_display", "urgente",
            "instrucoes", "resultado_arquivo", "resultado_texto",
            "data_solicitacao", "data_realizacao",
        ]
        read_only_fields = ["id", "medico", "data_solicitacao"]


class SolicitacaoExameCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitacaoExame
        fields = [
            "consulta", "paciente", "tipo_exame",
            "urgente", "instrucoes",
        ]
