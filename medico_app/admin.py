from django.contrib import admin
from django.utils.html import format_html
from .models import Medico, Disponibilidade
from .models_plano import AssinaturaMedico

# Registra admin de Plano e AssinaturaMedico
import medico_app.admin_plano  # noqa: F401


class DisponibilidadeInline(admin.TabularInline):
    model = Disponibilidade
    extra = 0
    fields = ('dia_semana', 'hora_inicio', 'hora_fim', 'duracao_consulta_min', 'ativo')


class AssinaturaMedicoInline(admin.StackedInline):
    """Mostra o plano ativo do médico inline no admin do Médico."""
    model = AssinaturaMedico
    extra = 0
    max_num = 1
    fields = (
        'plano', 'status',
        'transcricoes_usadas', 'assinaturas_usadas',
        'ciclo_inicio', 'ciclo_fim',
    )
    readonly_fields = ('transcricoes_usadas', 'assinaturas_usadas')


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    inlines = (DisponibilidadeInline, AssinaturaMedicoInline)
    list_display = (
        '__str__', 'especialidade', 'crm_estado',
        'plano_atual', 'is_govbr_linked', 'atende_convenio', 'created_at',
    )
    list_filter = ('especialidade', 'crm_estado', 'is_govbr_linked', 'atende_convenio')
    search_fields = ('user__email', 'user__nome_completo', 'crm')
    raw_id_fields = ('user', 'clinica_principal')
    readonly_fields = ('created_at', 'updated_at')

    def plano_atual(self, obj):
        assinatura = getattr(obj, "assinatura", None)
        if not assinatura:
            return format_html('<span style="color: gray;">Sem plano</span>')
        cores = {
            "starter": "#6c757d",
            "professional": "#0d6efd",
            "enterprise": "#6f42c1",
        }
        cor = cores.get(assinatura.plano.tipo, "#333")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 6px; '
            'border-radius:3px; font-size:11px;">{}</span>',
            cor, assinatura.plano.nome,
        )
    plano_atual.short_description = "Plano"

