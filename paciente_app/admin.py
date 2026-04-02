from django.contrib import admin
from .models import Paciente, Prontuario


class ProntuarioInline(admin.TabularInline):
    model = Prontuario
    extra = 0
    fields = ('data_consulta', 'medico', 'queixa_principal', 'diagnostico_cid10')
    readonly_fields = ('data_consulta', 'created_at')
    show_change_link = True


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    inlines = (ProntuarioInline,)
    list_display = ('__str__', 'tipo_sanguineo', 'convenio_nome', 'medico_principal', 'created_at')
    list_filter = ('tipo_sanguineo',)
    search_fields = ('user__email', 'user__nome_completo')
    raw_id_fields = ('user', 'medico_principal')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Prontuario)
class ProntuarioAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'data_consulta', 'diagnostico_cid10', 'created_at')
    list_filter = ('data_consulta',)
    search_fields = ('paciente__user__email', 'medico__user__nome_completo', 'diagnostico_cid10')
    raw_id_fields = ('paciente', 'medico')
    readonly_fields = ('created_at', 'updated_at')
