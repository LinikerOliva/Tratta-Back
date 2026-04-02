"""
paciente_app/models.py
Modelos do domínio Paciente.
"""
from django.db import models
from django.conf import settings


class Paciente(models.Model):
    """Perfil de paciente — extensão do CustomUser para role='paciente'."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paciente",
        limit_choices_to={"role": "paciente"},
    )
    data_nascimento = models.DateField(verbose_name="Data de nascimento")
    tipo_sanguineo = models.CharField(
        max_length=5,
        blank=True,
        choices=[
            ("A+", "A+"), ("A-", "A-"),
            ("B+", "B+"), ("B-", "B-"),
            ("AB+", "AB+"), ("AB-", "AB-"),
            ("O+", "O+"), ("O-", "O-"),
        ],
    )
    peso_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Peso (kg)")
    altura_cm = models.IntegerField(null=True, blank=True, verbose_name="Altura (cm)")
    alergias = models.TextField(blank=True, verbose_name="Alergias conhecidas")
    doencas_cronicas = models.TextField(
        blank=True, 
        verbose_name="Doenças crônicas",
        help_text="(Armazenamento sensível com criptografia extra simulada na camada DB)"
    )
    medicamentos_uso_continuo = models.TextField(blank=True)
    convenio_nome = models.CharField(max_length=100, blank=True, verbose_name="Convênio")
    convenio_numero = models.CharField(max_length=50, blank=True, verbose_name="Número do plano")
    medico_principal = models.ForeignKey(
        "medico_app.Medico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pacientes_principals",
    )
    notificacoes_whatsapp = models.BooleanField(
        default=True,
        verbose_name="Notificações via WhatsApp"
    )
    notificacoes_email = models.BooleanField(
        default=True,
        verbose_name="Notificações via E-mail"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "paciente_app"
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return f"Paciente: {self.user.nome_completo}"

    @property
    def idade(self) -> int:
        from datetime import date
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )


class Prontuario(models.Model):
    """Registro de prontuário médico."""

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="prontuarios",
    )
    medico = models.ForeignKey(
        "medico_app.Medico",
        on_delete=models.PROTECT,
        related_name="prontuarios_criados",
    )
    data_consulta = models.DateTimeField(verbose_name="Data da consulta")
    queixa_principal = models.TextField(verbose_name="Queixa principal")
    anamnese = models.TextField(blank=True, verbose_name="Anamnese")
    exame_fisico = models.TextField(blank=True, verbose_name="Exame físico")
    hipotese_diagnostica = models.TextField(blank=True, verbose_name="Hipótese diagnóstica")
    diagnostico_cid10 = models.CharField(max_length=10, blank=True, verbose_name="CID-10")
    conduta = models.TextField(blank=True, verbose_name="Conduta médica")
    retorno_em = models.DateField(null=True, blank=True, verbose_name="Data do retorno")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "paciente_app"
        verbose_name = "Prontuário"
        verbose_name_plural = "Prontuários"
        ordering = ["-data_consulta"]

    def __str__(self):
        return f"Prontuário {self.paciente} — {self.data_consulta:%d/%m/%Y}"
