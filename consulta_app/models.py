"""
consulta_app/models.py
Modelos do domínio Consulta e Agendamento.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Agendamento(models.Model):
    """Agendamento de consulta (pré-consulta)."""

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        CONFIRMADO = "confirmado", "Confirmado"
        CANCELADO = "cancelado", "Cancelado"
        REAGENDADO = "reagendado", "Reagendado"

    paciente = models.ForeignKey(
        "paciente_app.Paciente",
        on_delete=models.CASCADE,
        related_name="agendamentos",
    )
    medico = models.ForeignKey(
        "medico_app.Medico",
        on_delete=models.CASCADE,
        related_name="agendamentos",
    )
    clinica = models.ForeignKey(
        "clinica_app.Clinica",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    data_hora = models.DateTimeField(verbose_name="Data e hora da consulta")
    motivo = models.TextField(blank=True, verbose_name="Motivo da consulta")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    observacoes_paciente = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agendamentos_criados",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "consulta_app"
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ["data_hora"]

    def __str__(self):
        return f"Agendamento {self.paciente} c/ {self.medico} em {self.data_hora:%d/%m/%Y %H:%M}"


class Consulta(models.Model):
    """Consulta realizada (pós-atendimento)."""

    class Status(models.TextChoices):
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        FINALIZADA = "finalizada", "Finalizada"
        CANCELADA = "cancelada", "Cancelada"

    agendamento = models.OneToOneField(
        Agendamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consulta",
    )
    paciente = models.ForeignKey(
        "paciente_app.Paciente",
        on_delete=models.PROTECT,
        related_name="consultas",
    )
    medico = models.ForeignKey(
        "medico_app.Medico",
        on_delete=models.PROTECT,
        related_name="consultas",
    )
    data_inicio = models.DateTimeField(default=timezone.now)
    data_fim = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EM_ANDAMENTO)
    resumo = models.TextField(blank=True)

    # ── Transcrição Voice-to-Text (LGPD: apenas texto, sem áudio bruto) ──
    transcricao_texto = models.TextField(
        blank=True,
        verbose_name="Transcrição processada",
        help_text="Texto transcrito da consulta. Áudio bruto NÃO é armazenado (LGPD).",
    )
    # ── Campos estruturados pela IA ──────────────────────────────────────
    queixa_principal = models.TextField(
        blank=True,
        verbose_name="Queixa principal",
        help_text="Extraído automaticamente pela IA a partir da transcrição.",
    )
    anamnese = models.TextField(
        blank=True,
        verbose_name="Anamnese",
        help_text="Estruturada automaticamente pela IA.",
    )
    hipotese_diagnostica = models.TextField(
        blank=True,
        verbose_name="Hipótese diagnóstica",
        help_text="Sugerida automaticamente pela IA.",
    )
    # ── Métricas de produtividade ────────────────────────────────────────
    duracao_segundos = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Duração da consulta (segundos)",
        help_text="Calculado automaticamente ao finalizar.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "consulta_app"
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ["-data_inicio"]

    def __str__(self):
        return f"Consulta #{self.id} — {self.paciente} c/ {self.medico}"
