from django.contrib import admin
from .models import Agendamento, Consulta


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'data_hora', 'clinica', 'criado_por', 'created_at')
    list_filter = ('status', 'data_hora')
    search_fields = ('paciente__user__nome_completo', 'medico__user__nome_completo')
    raw_id_fields = ('paciente', 'medico', 'clinica', 'criado_por')
    readonly_fields = ('created_at',)
    date_hierarchy = 'data_hora'


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'data_inicio', 'data_fim')
    list_filter = ('status',)
    search_fields = ('paciente__user__nome_completo', 'medico__user__nome_completo')
    raw_id_fields = ('agendamento', 'paciente', 'medico')
    readonly_fields = ('created_at',)
    date_hierarchy = 'data_inicio'
