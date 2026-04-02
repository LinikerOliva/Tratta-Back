from django.contrib import admin
from .models import Clinica, Secretaria


class SecretariaInline(admin.TabularInline):
    model = Secretaria
    extra = 0
    fields = ('user', 'cargo', 'pode_agendar', 'pode_ver_prontuario')
    raw_id_fields = ('user',)


@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    inlines = (SecretariaInline,)
    list_display = ('nome_fantasia', 'cnpj', 'telefone', 'email_contato', 'ativa', 'created_at')
    list_filter = ('ativa',)
    search_fields = ('nome_fantasia', 'razao_social', 'cnpj')
    raw_id_fields = ('user',)
    filter_horizontal = ('medicos',)
    readonly_fields = ('created_at',)


@admin.register(Secretaria)
class SecretariaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'clinica', 'cargo', 'pode_agendar', 'pode_ver_prontuario')
    search_fields = ('user__nome_completo', 'user__email', 'clinica__nome_fantasia')
    raw_id_fields = ('user', 'clinica')
