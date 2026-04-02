"""
clinica_app/models.py
Modelos do domínio Clínica e Secretaria.
"""
from django.db import models
from django.conf import settings


class Clinica(models.Model):
    """Clínica médica cadastrada no sistema."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clinica",
        limit_choices_to={"role": "clinica"},
    )
    nome_fantasia = models.CharField(max_length=200, verbose_name="Nome fantasia")
    razao_social = models.CharField(max_length=200, blank=True, verbose_name="Razão social")
    cnpj = models.CharField(max_length=14, unique=True, verbose_name="CNPJ")
    telefone = models.CharField(max_length=20, blank=True)
    email_contato = models.EmailField(blank=True)
    endereco = models.TextField(blank=True)
    logo = models.ImageField(upload_to="clinicas/logos/", null=True, blank=True)
    horario_funcionamento = models.CharField(max_length=200, blank=True)
    medicos = models.ManyToManyField(
        "medico_app.Medico",
        related_name="clinicas",
        blank=True,
        verbose_name="Médicos da clínica",
    )
    protocolo_manchester_ativo = models.BooleanField(
        default=False, 
        verbose_name="Protocolo de Manchester na Fila"
    )
    ativa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "clinica_app"
        verbose_name = "Clínica"
        verbose_name_plural = "Clínicas"

    def __str__(self):
        return self.nome_fantasia


class Secretaria(models.Model):
    """Secretaria vinculada a uma clínica."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="secretaria",
        limit_choices_to={"role": "secretaria"},
    )
    clinica = models.ForeignKey(
        Clinica,
        on_delete=models.CASCADE,
        related_name="secretarias",
    )
    cargo = models.CharField(max_length=100, blank=True)
    pode_agendar = models.BooleanField(default=True)
    pode_ver_prontuario = models.BooleanField(default=False)

    class Meta:
        app_label = "clinica_app"
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"

    def __str__(self):
        return f"{self.user.nome_completo} — {self.clinica.nome_fantasia}"
