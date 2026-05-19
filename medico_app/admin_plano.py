"""
medico_app/admin_plano.py
Configuração do Django Admin para gestão de Planos e Assinaturas.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models_plano import Plano, AssinaturaMedico


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    """
    Admin do catálogo de planos.
    Permite criar, editar e desativar planos.
    """

    list_display = (
        "nome", "tipo", "preco_formatado",
        "limite_transcricoes_display", "limite_assinaturas_display",
        "tem_dashboard_avancado", "ativo", "total_assinantes",
    )
    list_filter = ("tipo", "ativo", "tem_dashboard_avancado")
    search_fields = ("nome", "tipo")
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("ativo",)

    fieldsets = (
        ("Identificação", {
            "fields": ("nome", "tipo", "descricao", "preco_mensal", "ativo"),
        }),
        ("Limites de Recursos", {
            "fields": ("limite_transcricoes", "limite_assinaturas"),
            "description": "Use 0 (zero) para recursos ilimitados.",
        }),
        ("Feature Flags", {
            "fields": (
                "tem_dashboard_avancado", "tem_suporte_prioritario",
                "tem_multi_usuarios", "tem_relatorios_faturamento",
            ),
        }),
        ("Auditoria", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def preco_formatado(self, obj):
        if obj.preco_mensal == 0:
            return format_html('<span style="color: green;">Gratuito</span>')
        return f"R$ {obj.preco_mensal}"
    preco_formatado.short_description = "Preço"
    preco_formatado.admin_order_field = "preco_mensal"

    def limite_transcricoes_display(self, obj):
        if obj.transcricoes_ilimitadas:
            return format_html('<span style="color: green;">∞ Ilimitado</span>')
        return f"{obj.limite_transcricoes}/mês"
    limite_transcricoes_display.short_description = "Transcrições"

    def limite_assinaturas_display(self, obj):
        if obj.assinaturas_ilimitadas:
            return format_html('<span style="color: green;">∞ Ilimitado</span>')
        return f"{obj.limite_assinaturas}/mês"
    limite_assinaturas_display.short_description = "Assinaturas"

    def total_assinantes(self, obj):
        count = obj.assinaturas.filter(status__in=["ativa", "trial"]).count()
        return count
    total_assinantes.short_description = "Assinantes ativos"


@admin.register(AssinaturaMedico)
class AssinaturaMedicoAdmin(admin.ModelAdmin):
    """
    Admin de assinaturas dos médicos.
    Mostra o plano ativo e consumo de recursos.
    """

    list_display = (
        "medico", "plano_badge", "status_badge",
        "consumo_transcricoes", "consumo_assinaturas",
        "ciclo_display",
    )
    list_filter = ("status", "plano__tipo")
    search_fields = (
        "medico__user__nome_completo",
        "medico__user__email",
        "medico__crm",
    )
    raw_id_fields = ("medico",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("medico__user", "plano")

    fieldsets = (
        ("Vínculo", {
            "fields": ("medico", "plano", "status"),
        }),
        ("Consumo do Ciclo", {
            "fields": (
                "transcricoes_usadas", "assinaturas_usadas",
                "ciclo_inicio", "ciclo_fim",
            ),
        }),
        ("Gateway de Pagamento", {
            "fields": ("gateway_customer_id", "gateway_subscription_id"),
            "classes": ("collapse",),
            "description": "Campos para futura integração com Stripe/Mercado Pago.",
        }),
        ("Auditoria", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["resetar_ciclo_selecionados"]

    def plano_badge(self, obj):
        cores = {
            "starter": "#6c757d",
            "professional": "#0d6efd",
            "enterprise": "#6f42c1",
        }
        cor = cores.get(obj.plano.tipo, "#333")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; '
            'border-radius:4px; font-size:11px;">{}</span>',
            cor, obj.plano.nome,
        )
    plano_badge.short_description = "Plano"

    def status_badge(self, obj):
        cores = {
            "ativa": "green",
            "trial": "orange",
            "suspensa": "red",
            "cancelada": "gray",
        }
        cor = cores.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            cor, obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def consumo_transcricoes(self, obj):
        if obj.plano.transcricoes_ilimitadas:
            return f"{obj.transcricoes_usadas} / ∞"
        pct = (obj.transcricoes_usadas / obj.plano.limite_transcricoes * 100) if obj.plano.limite_transcricoes else 0
        cor = "red" if pct >= 90 else "orange" if pct >= 70 else "green"
        return format_html(
            '{} / {} <span style="color:{};">({}%)</span>',
            obj.transcricoes_usadas, obj.plano.limite_transcricoes,
            cor, int(pct),
        )
    consumo_transcricoes.short_description = "IA (usadas/limite)"

    def consumo_assinaturas(self, obj):
        if obj.plano.assinaturas_ilimitadas:
            return f"{obj.assinaturas_usadas} / ∞"
        pct = (obj.assinaturas_usadas / obj.plano.limite_assinaturas * 100) if obj.plano.limite_assinaturas else 0
        cor = "red" if pct >= 90 else "orange" if pct >= 70 else "green"
        return format_html(
            '{} / {} <span style="color:{};">({}%)</span>',
            obj.assinaturas_usadas, obj.plano.limite_assinaturas,
            cor, int(pct),
        )
    consumo_assinaturas.short_description = "Gov.br (usadas/limite)"

    def ciclo_display(self, obj):
        return f"{obj.ciclo_inicio:%d/%m} → {obj.ciclo_fim:%d/%m/%Y}"
    ciclo_display.short_description = "Ciclo"

    @admin.action(description="🔄 Resetar ciclo dos selecionados")
    def resetar_ciclo_selecionados(self, request, queryset):
        count = 0
        for assinatura in queryset:
            assinatura.resetar_ciclo()
            count += 1
        self.message_user(request, f"Ciclo resetado para {count} assinatura(s).")
