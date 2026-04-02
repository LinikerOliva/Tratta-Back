"""
exame_app/models.py
Modelos do domínio Exames.
"""
from django.db import models


class TipoExame(models.Model):
    """Catálogo de tipos de exame."""
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    codigo_cbhpm = models.CharField(max_length=20, blank=True, verbose_name="Código CBHPM")
    requer_jejum = models.BooleanField(default=False)
    instrucoes_preparo = models.TextField(blank=True)

    class Meta:
        app_label = "exame_app"
        verbose_name = "Tipo de Exame"

    def __str__(self):
        return self.nome


class SolicitacaoExame(models.Model):
    """Solicitação de exame pelo médico."""

    class Status(models.TextChoices):
        SOLICITADO = "solicitado", "Solicitado"
        REALIZADO = "realizado", "Realizado"
        RESULTADO_DISPONIVEL = "resultado_disponivel", "Resultado Disponível"
        CANCELADO = "cancelado", "Cancelado"

    consulta = models.ForeignKey(
        "consulta_app.Consulta",
        on_delete=models.CASCADE,
        related_name="exames_solicitados",
        null=True,
        blank=True,
    )
    paciente = models.ForeignKey(
        "paciente_app.Paciente",
        on_delete=models.PROTECT,
        related_name="exames",
    )
    medico = models.ForeignKey(
        "medico_app.Medico",
        on_delete=models.PROTECT,
        related_name="exames_solicitados",
    )
    tipo_exame = models.ForeignKey(TipoExame, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SOLICITADO)
    urgente = models.BooleanField(default=False)
    instrucoes = models.TextField(blank=True)
    resultado_arquivo = models.FileField(
        upload_to="exames/resultados/",
        null=True,
        blank=True,
    )
    resultado_texto = models.TextField(blank=True)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_realizacao = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "exame_app"
        verbose_name = "Solicitação de Exame"
        verbose_name_plural = "Solicitações de Exame"
        ordering = ["-data_solicitacao"]

    def __str__(self):
        return f"Exame {self.tipo_exame} — {self.paciente} [{self.status}]"
