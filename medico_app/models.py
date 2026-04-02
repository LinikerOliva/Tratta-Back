"""
medico_app/models.py
Modelos do domínio Médico.
"""
from django.db import models
from django.conf import settings


class Medico(models.Model):
    """
    Perfil médico — extensão do CustomUser para usuários com role='medico'.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medico",
        verbose_name="Usuário",
        limit_choices_to={"role": "medico"},
    )
    crm = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="CRM",
        help_text="Número do Conselho Regional de Medicina.",
    )
    crm_estado = models.CharField(
        max_length=2,
        verbose_name="Estado do CRM",
        help_text="UF do CRM. Ex: SP, RJ, MG.",
    )
    especialidade = models.CharField(
        max_length=100,
        verbose_name="Especialidade médica",
    )
    rqe = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="RQE",
        help_text="Registro de Qualificação de Especialista.",
    )
    sub_especialidades = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Sub-especialidades",
        help_text="Separadas por vírgula.",
    )
    assinatura_img = models.ImageField(
        upload_to="assinaturas/",
        null=True,
        blank=True,
        verbose_name="Imagem da assinatura",
        help_text="Assinatura manuscrita digitalizada (PNG/JPEG).",
    )
    # ── Gov.br ───────────────────────────────────────────────────────────────
    govbr_sub = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Subject Gov.br",
        help_text="Identificador único do médico no Gov.br (hash CPF).",
    )
    is_govbr_linked = models.BooleanField(
        default=False,
        verbose_name="Gov.br vinculado",
        help_text="True quando o médico autorizou assinatura via Gov.br.",
    )
    # ── Clínica principal ─────────────────────────────────────────────────────
    clinica_principal = models.ForeignKey(
        "clinica_app.Clinica",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicos_principais",
        verbose_name="Clínica principal",
    )
    bio = models.TextField(
        blank=True,
        verbose_name="Biografia",
        help_text="Apresentação profissional do médico.",
    )
    atende_convenio = models.BooleanField(
        default=True,
        verbose_name="Atende convênio",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "medico_app"
        verbose_name = "Médico"
        verbose_name_plural = "Médicos"
        ordering = ["user__nome_completo"]

    def __str__(self):
        return f"Dr(a). {self.user.nome_completo} — CRM/{self.crm_estado} {self.crm}"

    @property
    def nome_completo(self):
        return self.user.nome_completo

    @property
    def pode_assinar(self) -> bool:
        """Médico pode assinar digitalmente se vinculou ao Gov.br."""
        return self.is_govbr_linked


class Disponibilidade(models.Model):
    """Slots de agenda do médico por dia da semana."""

    class DiaSemana(models.IntegerChoices):
        SEGUNDA = 0, "Segunda-feira"
        TERCA = 1, "Terça-feira"
        QUARTA = 2, "Quarta-feira"
        QUINTA = 3, "Quinta-feira"
        SEXTA = 4, "Sexta-feira"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name="disponibilidades",
    )
    dia_semana = models.IntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField(verbose_name="Hora de início")
    hora_fim = models.TimeField(verbose_name="Hora de término")
    duracao_consulta_min = models.PositiveIntegerField(
        default=30,
        verbose_name="Duração da consulta (min)",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        app_label = "medico_app"
        verbose_name = "Disponibilidade"
        verbose_name_plural = "Disponibilidades"
        unique_together = [("medico", "dia_semana", "hora_inicio")]
        ordering = ["dia_semana", "hora_inicio"]

    def __str__(self):
        return f"{self.medico} — {self.get_dia_semana_display()} {self.hora_inicio}—{self.hora_fim}"


class ReceituarioConfig(models.Model):
    """Configurações visuais do receituário do médico (Business/Layout)."""
    
    medico = models.OneToOneField(
        Medico,
        on_delete=models.CASCADE,
        related_name="receituario_config",
        primary_key=True
    )
    logotipo_clinica = models.ImageField(upload_to="receituarios/logos/", null=True, blank=True)
    cabecalho = models.TextField(blank=True, help_text="Texto do cabeçalho da receita.")
    rodape = models.TextField(blank=True, help_text="Texto do rodapé da receita.")
    fonte_nome = models.CharField(max_length=50, default="Arial", verbose_name="Fonte")
    margem_superior = models.IntegerField(default=20, verbose_name="Margem Superior (mm)")
    margem_inferior = models.IntegerField(default=20, verbose_name="Margem Inferior (mm)")
    margem_esquerda = models.IntegerField(default=20, verbose_name="Margem Esquerda (mm)")
    margem_direita = models.IntegerField(default=20, verbose_name="Margem Direita (mm)")
    
    class Meta:
        app_label = "medico_app"
        verbose_name = "Configuração de Receituário"
        verbose_name_plural = "Configurações de Receituário"

    def __str__(self):
        return f"Receituário - {self.medico}"
