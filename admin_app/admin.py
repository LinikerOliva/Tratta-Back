from django.contrib import admin
from .models import SolicitacaoCadastro


@admin.register(SolicitacaoCadastro)
class SolicitacaoCadastroAdmin(admin.ModelAdmin):
    list_display = ('solicitante', 'tipo', 'status', 'avaliado_por', 'created_at')
    list_filter = ('tipo', 'status')
    search_fields = ('solicitante__email', 'solicitante__nome_completo')
    raw_id_fields = ('solicitante', 'avaliado_por')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['aprovar', 'rejeitar']

    @admin.action(description='✅ Aprovar solicitações selecionadas')
    def aprovar(self, request, queryset):
        queryset.update(status=SolicitacaoCadastro.Status.APROVADA, avaliado_por=request.user)
        self.message_user(request, f'{queryset.count()} solicitação(ões) aprovada(s).')

    @admin.action(description='❌ Rejeitar solicitações selecionadas')
    def rejeitar(self, request, queryset):
        queryset.update(status=SolicitacaoCadastro.Status.REJEITADA, avaliado_por=request.user)
        self.message_user(request, f'{queryset.count()} solicitação(ões) rejeitada(s).')
