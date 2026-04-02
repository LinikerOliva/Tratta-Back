from django.contrib import admin
from .models import Medico, Disponibilidade


class DisponibilidadeInline(admin.TabularInline):
    model = Disponibilidade
    extra = 0
    fields = ('dia_semana', 'hora_inicio', 'hora_fim', 'duracao_consulta_min', 'ativo')


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    inlines = (DisponibilidadeInline,)
    list_display = ('__str__', 'especialidade', 'crm_estado', 'is_govbr_linked', 'atende_convenio', 'created_at')
    list_filter = ('especialidade', 'crm_estado', 'is_govbr_linked', 'atende_convenio')
    search_fields = ('user__email', 'user__nome_completo', 'crm')
    raw_id_fields = ('user', 'clinica_principal')
    readonly_fields = ('created_at', 'updated_at')
