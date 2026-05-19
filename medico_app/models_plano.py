"""
medico_app/models_plano.py
Modelos de Plano de Assinatura e controle de consumo mensal.

Arquitetura:
- Plano: Catálogo de planos (Starter, Professional, Enterprise).
- AssinaturaMedico: Vínculo 1:1 entre Medico e seu plano ativo,
  com campos de consumo e controle de ciclo mensal.
"""
from django.db import models
from django.utils import timezone


class Plano(models.Model):
    """
    Catálogo de planos de assinatura do Tratta.

    Gerenciado pelo Admin. O frontend consulta os limites para
    bloquear/liberar funcionalidades na UI.
    """

    class Tipo(models.TextChoices):
        STARTER = "starter", "Starter"
        PROFESSIONAL = "professional", "Professional"
        ENTERPRISE = "enterprise", "Enterprise"

    nome = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nome do plano",
    )
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        unique=True,
        verbose_name="Tipo",
        help_text="Identificador interno do plano.",
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Descrição comercial para exibição.",
    )
    preco_mensal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Preço mensal (R$)",
        help_text="Preço mensal do plano. 0 = gratuito/trial.",
    )
    preco_promocional = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Preço Promocional (R$)",
        help_text="Preço com desconto. Se preenchido, substitui o preço mensal.",
    )

    # ── Limites de recursos ──────────────────────────────────────────────
    limite_transcricoes = models.IntegerField(
        default=20,
        verbose_name="Limite de transcrições/mês",
        help_text="0 = ilimitado.",
    )
    limite_assinaturas = models.IntegerField(
        default=30,
        verbose_name="Limite de assinaturas Gov.br/mês",
        help_text="0 = ilimitado.",
    )

    # ── Feature flags ────────────────────────────────────────────────────
    tem_dashboard_avancado = models.BooleanField(
        default=False,
        verbose_name="Dashboard avançado",
        help_text="Libera gráficos de tempo médio e produtividade.",
    )
    tem_suporte_prioritario = models.BooleanField(
        default=False,
        verbose_name="Suporte prioritário",
    )
    tem_multi_usuarios = models.BooleanField(
        default=False,
        verbose_name="Multi-usuários",
        help_text="Permite vários médicos na mesma conta (Enterprise).",
    )
    tem_relatorios_faturamento = models.BooleanField(
        default=False,
        verbose_name="Relatórios de faturamento",
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Plano ativo",
        help_text="Desmarque para desativar o plano (soft-delete).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "medico_app"
        verbose_name = "Plano de Assinatura"
        verbose_name_plural = "Planos de Assinatura"
        ordering = ["preco_mensal"]

    def __str__(self):
        return f"{self.nome} (R$ {self.preco_mensal}/mês)"

    @property
    def transcricoes_ilimitadas(self) -> bool:
        return self.limite_transcricoes == 0

    @property
    def assinaturas_ilimitadas(self) -> bool:
        return self.limite_assinaturas == 0


class AssinaturaMedico(models.Model):
    """
    Vínculo 1:1 entre Médico e seu Plano ativo.

    Controla o consumo mensal de recursos e a data de renovação.
    Preparado para futura integração com gateway de pagamento
    (Stripe customer_id, subscription_id).
    """

    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        CANCELADA = "cancelada", "Cancelada"
        SUSPENSA = "suspensa", "Suspensa"
        TRIAL = "trial", "Trial"

    medico = models.OneToOneField(
        "medico_app.Medico",
        on_delete=models.CASCADE,
        related_name="assinatura",
        verbose_name="Médico",
    )
    plano = models.ForeignKey(
        Plano,
        on_delete=models.PROTECT,
        related_name="assinaturas",
        verbose_name="Plano",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVA,
        verbose_name="Status da assinatura",
    )

    # ── Consumo do ciclo atual ───────────────────────────────────────────
    transcricoes_usadas = models.PositiveIntegerField(
        default=0,
        verbose_name="Transcrições usadas no mês",
    )
    assinaturas_usadas = models.PositiveIntegerField(
        default=0,
        verbose_name="Assinaturas Gov.br usadas no mês",
    )

    # ── Controle de ciclo ────────────────────────────────────────────────
    ciclo_inicio = models.DateField(
        verbose_name="Início do ciclo atual",
        help_text="Data de início do período de faturamento.",
    )
    ciclo_fim = models.DateField(
        verbose_name="Fim do ciclo atual",
        help_text="Data de término do período (próximo reset).",
    )

    # ── Preparação para gateway de pagamento ─────────────────────────────
    gateway_customer_id = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="ID do cliente no gateway",
        help_text="Ex: cus_xxxx (Stripe) ou customer_id (Mercado Pago).",
    )
    gateway_subscription_id = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="ID da assinatura no gateway",
        help_text="Ex: sub_xxxx (Stripe) ou preapproval_id (Mercado Pago).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "medico_app"
        verbose_name = "Assinatura do Médico"
        verbose_name_plural = "Assinaturas dos Médicos"

    def __str__(self):
        return f"{self.medico} → {self.plano.nome} [{self.status}]"

    # ── Métodos de verificação de saldo ──────────────────────────────────

    @property
    def transcricoes_restantes(self) -> int | None:
        """Retorna transcrições restantes. None = ilimitado."""
        if self.plano.transcricoes_ilimitadas:
            return None
        return max(0, self.plano.limite_transcricoes - self.transcricoes_usadas)

    @property
    def assinaturas_restantes(self) -> int | None:
        """Retorna assinaturas restantes. None = ilimitado."""
        if self.plano.assinaturas_ilimitadas:
            return None
        return max(0, self.plano.limite_assinaturas - self.assinaturas_usadas)

    def pode_transcrever(self) -> bool:
        """Verifica se o médico ainda pode usar transcrição IA."""
        if self.status not in (self.Status.ATIVA, self.Status.TRIAL):
            return False
        if self.plano.transcricoes_ilimitadas:
            return True
        return self.transcricoes_usadas < self.plano.limite_transcricoes

    def pode_assinar_govbr(self) -> bool:
        """Verifica se o médico ainda pode assinar via Gov.br."""
        if self.status not in (self.Status.ATIVA, self.Status.TRIAL):
            return False
        if self.plano.assinaturas_ilimitadas:
            return True
        return self.assinaturas_usadas < self.plano.limite_assinaturas

    def consumir_transcricao(self) -> bool:
        """
        Consome 1 transcrição do saldo.
        Retorna True se consumiu com sucesso, False se sem saldo.
        """
        if not self.pode_transcrever():
            return False
        self.transcricoes_usadas += 1
        self.save(update_fields=["transcricoes_usadas", "updated_at"])
        return True

    def consumir_assinatura(self) -> bool:
        """
        Consome 1 assinatura Gov.br do saldo.
        Retorna True se consumiu com sucesso, False se sem saldo.
        """
        if not self.pode_assinar_govbr():
            return False
        self.assinaturas_usadas += 1
        self.save(update_fields=["assinaturas_usadas", "updated_at"])
        return True

    def resetar_ciclo(self):
        """Reseta contadores e avança o ciclo para o próximo mês."""
        from dateutil.relativedelta import relativedelta

        self.transcricoes_usadas = 0
        self.assinaturas_usadas = 0
        self.ciclo_inicio = self.ciclo_fim
        self.ciclo_fim = self.ciclo_fim + relativedelta(months=1)
        self.save(update_fields=[
            "transcricoes_usadas", "assinaturas_usadas",
            "ciclo_inicio", "ciclo_fim", "updated_at",
        ])

    @property
    def is_ativa(self) -> bool:
        return self.status in (self.Status.ATIVA, self.Status.TRIAL)
