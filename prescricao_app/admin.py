from django.contrib import admin
from .models import Medicamento, Receita, ItemReceita, TemplateReceita


class ItemReceitaInline(admin.TabularInline):
    model = ItemReceita
    extra = 0
    fields = ('medicamento', 'dosagem', 'quantidade', 'posologia', 'via_administracao', 'duracao_tratamento', 'ordem')


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    inlines = (ItemReceitaInline,)
    list_display = ('__str__', 'medico', 'paciente', 'tipo', 'status', 'data_emissao', 'via_govbr')
    list_filter = ('tipo', 'status', 'via_govbr')
    search_fields = ('medico__user__nome_completo', 'paciente__user__nome_completo', 'hash_verificacao')
    raw_id_fields = ('medico', 'paciente', 'consulta')
    readonly_fields = ('data_emissao', 'hash_conteudo', 'hash_verificacao', 'assinada_em', 'created_at', 'updated_at')


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'principio_ativo', 'concentracao', 'tipo', 'registro_anvisa', 'ativo')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome', 'principio_ativo', 'registro_anvisa')


@admin.register(TemplateReceita)
class TemplateReceitaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'medico', 'tipo_receita', 'ativo', 'created_at')
    list_filter = ('tipo_receita', 'ativo')
    search_fields = ('nome', 'medico__user__nome_completo')
    raw_id_fields = ('medico',)
