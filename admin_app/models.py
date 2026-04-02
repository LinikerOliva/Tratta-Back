"""
admin_app/models.py
Modelos do módulo administrativo — solicitações de cadastro e aprovações.
"""
from django.db import models
from django.conf import settings


class SolicitacaoCadastro(models.Model):
    """
    Solicitação de cadastro de médico, clínica ou secretaria.
    Requires aprovação do admin antes de ativar o acesso.
    """

    class Tipo(models.TextChoices):
        MEDICO = "medico", "Médico"
        CLINICA = "clinica", "Clínica"
        SECRETARIA = "secretaria", "Secretaria"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_ANALISE = "em_analise", "Em Análise"
        APROVADA = "aprovada", "Aprovada"
        REJEITADA = "rejeitada", "Rejeitada"

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitacoes_cadastro",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    dados_adicionais = models.JSONField(
        verbose_name="Dados da solicitação",
        help_text="CRM para médicos, CNPJ para clínicas, etc.",
    )
    documento_comprobatorio = models.FileField(
        upload_to="solicitacoes/documentos/",
        null=True,
        blank=True,
        verbose_name="Documento comprobatório",
    )
    avaliado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_avaliadas",
    )
    motivo_rejeicao = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "admin_app"
        verbose_name = "Solicitação de Cadastro"
        verbose_name_plural = "Solicitações de Cadastro"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Solicitação {self.tipo} — {self.solicitante.email} [{self.status}]"
