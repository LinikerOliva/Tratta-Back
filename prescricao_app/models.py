"""
prescricao_app/models.py
Modelos do domínio Prescrição (Receitas).
Módulo mais complexo do sistema Trathea.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Medicamento(models.Model):
    """Catálogo de medicamentos do sistema."""

    class Tipo(models.TextChoices):
        SIMPLES = "simples", "Receita Simples"
        CONTROLADO = "controlado", "Receita Controlada (C1, C2)"
        ANTIMICROBIANO = "antimicrobiano", "Antimicrobiano (AM)"

    nome = models.CharField(max_length=200, db_index=True, verbose_name="Nome comercial")
    principio_ativo = models.CharField(max_length=200, verbose_name="Princípio ativo")
    concentracao = models.CharField(max_length=100, blank=True, verbose_name="Concentração")
    forma_farmaceutica = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Forma farmacêutica",
        help_text="Ex: comprimido, cápsula, solução injetável",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.SIMPLES)
    registro_anvisa = models.CharField(max_length=50, blank=True, verbose_name="Registro ANVISA")
    ativo = models.BooleanField(default=True)

    class Meta:
        app_label = "prescricao_app"
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"
        ordering = ["nome"]
        indexes = [models.Index(fields=["nome", "principio_ativo"])]

    def __str__(self):
        return f"{self.nome} ({self.concentracao}) — {self.principio_ativo}"


class Receita(models.Model):
    """
    Receita médica — o modelo central do módulo de prescrição.
    Suporta assinatura digital via Gov.br com PAdES.
    """

    class Tipo(models.TextChoices):
        SIMPLES = "simples", "Receita Simples"
        CONTROLADA = "controlada", "Receita Controlada"
        ANTIMICROBIANO = "antimicrobiano", "Antimicrobiano"

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EMITIDA = "emitida", "Emitida"
        ASSINADA = "assinada", "Assinada Digitalmente"
        ENVIADA = "enviada", "Enviada ao Paciente"
        CANCELADA = "cancelada", "Cancelada"
        EXPIRADA = "expirada", "Expirada"

    # ── Relacionamentos ───────────────────────────────────────────────────────
    medico = models.ForeignKey(
        "medico_app.Medico",
        on_delete=models.PROTECT,
        related_name="receitas",
        verbose_name="Médico",
    )
    paciente = models.ForeignKey(
        "paciente_app.Paciente",
        on_delete=models.PROTECT,
        related_name="receitas",
        verbose_name="Paciente",
    )
    consulta = models.ForeignKey(
        "consulta_app.Consulta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receitas",
        verbose_name="Consulta de origem",
    )

    # ── Dados da Receita ──────────────────────────────────────────────────────
    tipo = models.CharField(max_length=20, choices=Tipo.choices, verbose_name="Tipo de receita")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RASCUNHO,
        db_index=True,
    )
    observacoes = models.TextField(blank=True, verbose_name="Observações clínicas")

    # ── Validade ──────────────────────────────────────────────────────────────
    data_emissao = models.DateTimeField(auto_now_add=True, verbose_name="Data de emissão")
    validade_dias = models.PositiveIntegerField(
        default=30,
        verbose_name="Validade (dias)",
    )

    # ── Segurança / Assinatura ────────────────────────────────────────────────
    hash_conteudo = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash SHA-256 do conteúdo",
        help_text="Hash do conteúdo serializado da receita para verificação de integridade.",
    )
    hash_verificacao = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Hash de verificação pública",
        help_text="Token público para verificação via QR Code (não contém dados sensíveis).",
        db_index=True,
    )
    assinatura_govbr = models.BinaryField(
        null=True,
        blank=True,
        verbose_name="Assinatura PAdES Gov.br",
        help_text="Assinatura PAdES retornada pela API de assinatura digital do Gov.br.",
    )
    via_govbr = models.BooleanField(
        default=False,
        verbose_name="Assinada via Gov.br",
    )
    assinada_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data/hora da assinatura digital",
    )

    # ── PDF ───────────────────────────────────────────────────────────────────
    pdf = models.FileField(
        upload_to="receitas/pdfs/",
        null=True,
        blank=True,
        verbose_name="PDF da receita",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "prescricao_app"
        verbose_name = "Receita"
        verbose_name_plural = "Receitas"
        ordering = ["-data_emissao"]
        indexes = [
            models.Index(fields=["medico", "status"]),
            models.Index(fields=["paciente", "status"]),
            models.Index(fields=["hash_verificacao"]),
        ]

    def __str__(self):
        return f"Receita #{self.id} — {self.tipo} [{self.status}]"

    @property
    def esta_expirada(self) -> bool:
        from datetime import timedelta
        if not self.data_emissao:
            return False
        expira_em = self.data_emissao + timedelta(days=self.validade_dias)
        return timezone.now() > expira_em

    @property
    def pode_ser_editada(self) -> bool:
        return self.status == self.Status.RASCUNHO

    @property
    def pode_ser_assinada(self) -> bool:
        return self.status in (self.Status.RASCUNHO, self.Status.EMITIDA)


class ItemReceita(models.Model):
    """Item individual de uma receita (medicamento + posologia)."""

    receita = models.ForeignKey(
        Receita,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="Receita",
    )
    medicamento = models.ForeignKey(
        Medicamento,
        on_delete=models.PROTECT,
        related_name="itens_receita",
        verbose_name="Medicamento",
    )
    dosagem = models.CharField(max_length=100, verbose_name="Dosagem")
    quantidade = models.CharField(max_length=50, verbose_name="Quantidade")
    posologia = models.TextField(verbose_name="Posologia / Modo de usar")
    via_administracao = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Via de administração",
        help_text="Ex: oral, intravenoso, tópico",
    )
    duracao_tratamento = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Duração do tratamento",
        help_text="Ex: 7 dias, 30 dias, uso contínuo",
    )
    instrucoes_especiais = models.TextField(
        blank=True,
        verbose_name="Instruções especiais",
        help_text="Alertas, jejum, interações medicamentosas, etc.",
    )
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem na receita")

    class Meta:
        app_label = "prescricao_app"
        verbose_name = "Item de Receita"
        verbose_name_plural = "Itens de Receita"
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.medicamento.nome} — {self.dosagem} × {self.quantidade}"


class TemplateReceita(models.Model):
    """Template reutilizável de receita criado pelo médico."""

    medico = models.ForeignKey(
        "medico_app.Medico",
        on_delete=models.CASCADE,
        related_name="templates_receitas",
    )
    nome = models.CharField(max_length=200, verbose_name="Nome do template")
    descricao = models.TextField(blank=True)
    tipo_receita = models.CharField(
        max_length=20,
        choices=Receita.Tipo.choices,
        default=Receita.Tipo.SIMPLES,
    )
    itens_json = models.JSONField(
        verbose_name="Itens do template",
        help_text="Snapshot serializado dos itens da receita.",
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "prescricao_app"
        verbose_name = "Template de Receita"
        verbose_name_plural = "Templates de Receita"
        ordering = ["nome"]

    def __str__(self):
        return f"Template: {self.nome} ({self.tipo_receita})"
