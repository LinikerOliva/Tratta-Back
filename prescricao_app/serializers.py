"""
prescricao_app/serializers.py
Serializers do módulo de prescrição.
"""
from rest_framework import serializers
from trathea_core.utils.sanitizers import sanitize_text
from prescricao_app.models import Receita, ItemReceita, Medicamento, TemplateReceita


class MedicamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicamento
        fields = ["id", "nome", "principio_ativo", "concentracao", "forma_farmaceutica", "tipo"]


class ItemReceitaSerializer(serializers.ModelSerializer):
    medicamento = MedicamentoSerializer(read_only=True)
    medicamento_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicamento.objects.filter(ativo=True),
        source="medicamento",
        write_only=True,
    )

    class Meta:
        model = ItemReceita
        fields = [
            "id", "medicamento", "medicamento_id",
            "dosagem", "quantidade", "posologia",
            "via_administracao", "duracao_tratamento",
            "instrucoes_especiais", "ordem",
        ]

    def validate_posologia(self, value):
        return sanitize_text(value)

    def validate_instrucoes_especiais(self, value):
        return sanitize_text(value)


class ReceitaSerializer(serializers.ModelSerializer):
    """Serializer completo para leitura."""
    itens = ItemReceitaSerializer(many=True, read_only=True)
    medico_nome = serializers.CharField(source="medico.user.nome_completo", read_only=True)
    paciente_nome = serializers.CharField(source="paciente.user.nome_completo", read_only=True)
    esta_expirada = serializers.BooleanField(read_only=True)
    pode_ser_editada = serializers.BooleanField(read_only=True)
    pode_ser_assinada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Receita
        fields = [
            "id", "tipo", "status",
            "medico", "medico_nome",
            "paciente", "paciente_nome",
            "consulta", "observacoes",
            "data_emissao", "validade_dias",
            "hash_verificacao", "via_govbr", "assinada_em",
            "pdf", "itens",
            "esta_expirada", "pode_ser_editada", "pode_ser_assinada",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "data_emissao",
            "hash_verificacao", "hash_conteudo",
            "via_govbr", "assinada_em", "assinatura_govbr",
            "created_at", "updated_at",
        ]


class ItemReceitaCreateSerializer(serializers.ModelSerializer):
    medicamento_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicamento.objects.filter(ativo=True),
        source="medicamento",
    )

    class Meta:
        model = ItemReceita
        fields = [
            "medicamento_id", "dosagem", "quantidade",
            "posologia", "via_administracao",
            "duracao_tratamento", "instrucoes_especiais", "ordem",
        ]


class ReceitaCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação e edição de receitas."""
    itens = ItemReceitaCreateSerializer(many=True)

    class Meta:
        model = Receita
        fields = [
            "tipo", "paciente", "consulta",
            "observacoes", "validade_dias", "itens",
        ]

    def validate_observacoes(self, value):
        return sanitize_text(value)

    def validate_itens(self, value):
        if not value:
            raise serializers.ValidationError("A receita deve ter pelo menos 1 medicamento.")
        if len(value) > 20:
            raise serializers.ValidationError("Uma receita não pode ter mais de 20 itens.")
        return value

    def validate(self, attrs):
        """Valida que o tipo da receita é compatível com os medicamentos."""
        tipo = attrs.get("tipo", "simples")
        itens = attrs.get("itens", [])

        # Receita simples não pode ter medicamentos controlados
        if tipo == "simples":
            for item in itens:
                med = item.get("medicamento")
                if med and med.tipo in ("controlado", "antimicrobiano"):
                    raise serializers.ValidationError({
                        "tipo": f"Receita 'simples' não pode conter medicamento controlado: {med.nome}. "
                                f"Use 'controlada' ou 'antimicrobiano'."
                    })
        return attrs

    def create(self, validated_data):
        itens_data = validated_data.pop("itens")
        request = self.context.get("request")

        receita = Receita.objects.create(
            medico=request.user.medico,
            **validated_data,
        )

        for item_data in itens_data:
            ItemReceita.objects.create(receita=receita, **item_data)

        return receita

    def update(self, instance, validated_data):
        itens_data = validated_data.pop("itens", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if itens_data is not None:
            instance.itens.all().delete()
            for item_data in itens_data:
                ItemReceita.objects.create(receita=instance, **item_data)

        return instance
