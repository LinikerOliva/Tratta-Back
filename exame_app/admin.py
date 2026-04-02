from django.contrib import admin
from .models import TipoExame, SolicitacaoExame


@admin.register(TipoExame)
class TipoExameAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_cbhpm', 'requer_jejum')
    list_filter = ('requer_jejum',)
    search_fields = ('nome', 'codigo_cbhpm')


@admin.register(SolicitacaoExame)
class SolicitacaoExameAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'paciente', 'medico', 'status', 'urgente', 'data_solicitacao', 'data_realizacao')
    list_filter = ('status', 'urgente')
    search_fields = ('paciente__user__nome_completo', 'medico__user__nome_completo', 'tipo_exame__nome')
    raw_id_fields = ('consulta', 'paciente', 'medico', 'tipo_exame')
    readonly_fields = ('data_solicitacao',)
    date_hierarchy = 'data_solicitacao'
