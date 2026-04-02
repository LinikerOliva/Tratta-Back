"""
Registro centralizado de todos os modelos do Trathea no Django Admin.
Importado em trathea_core/apps.py ou diretamente no settings.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# ── Core App ──────────────────────────────────────────────────────────────────
from core_app.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'nome_completo', 'role', 'is_active', 'is_verified', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_verified', 'is_staff', 'is_superuser')
    search_fields = ('email', 'nome_completo')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações Pessoais', {'fields': ('nome_completo', 'role')}),
        ('Permissões', {'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome_completo', 'role', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )
    # O CustomUser usa email como username
    filter_horizontal = ('groups', 'user_permissions')


# ── Paciente App ──────────────────────────────────────────────────────────────
try:
    from paciente_app.models import Paciente

    @admin.register(Paciente)
    class PacienteAdmin(admin.ModelAdmin):
        list_display = ('user', 'cpf', 'data_nascimento', 'telefone')
        search_fields = ('user__email', 'user__nome_completo', 'cpf')
        raw_id_fields = ('user',)
except Exception:
    pass


# ── Medico App ────────────────────────────────────────────────────────────────
try:
    from medico_app.models import Medico

    @admin.register(Medico)
    class MedicoAdmin(admin.ModelAdmin):
        list_display = ('user', 'crm', 'especialidade', 'is_approved')
        list_filter = ('is_approved', 'especialidade')
        search_fields = ('user__email', 'user__nome_completo', 'crm')
        raw_id_fields = ('user',)
except Exception:
    pass


# ── Clinica App ───────────────────────────────────────────────────────────────
try:
    from clinica_app.models import Clinica

    @admin.register(Clinica)
    class ClinicaAdmin(admin.ModelAdmin):
        list_display = ('nome', 'cnpj', 'user', 'is_approved')
        list_filter = ('is_approved',)
        search_fields = ('nome', 'cnpj', 'user__email')
        raw_id_fields = ('user',)
except Exception:
    pass


# ── Admin App ─────────────────────────────────────────────────────────────────
try:
    from admin_app.models import SolicitacaoCadastro

    @admin.register(SolicitacaoCadastro)
    class SolicitacaoCadastroAdmin(admin.ModelAdmin):
        list_display = ('user', 'role_solicitado', 'status', 'created_at')
        list_filter = ('role_solicitado', 'status')
        search_fields = ('user__email', 'user__nome_completo')
        readonly_fields = ('created_at',)
        raw_id_fields = ('user',)
except Exception:
    pass


# ── Exame App ─────────────────────────────────────────────────────────────────
try:
    from exame_app.models import TipoExame, SolicitacaoExame

    @admin.register(TipoExame)
    class TipoExameAdmin(admin.ModelAdmin):
        list_display = ('nome',)
        search_fields = ('nome',)

    @admin.register(SolicitacaoExame)
    class SolicitacaoExameAdmin(admin.ModelAdmin):
        list_display = ('paciente', 'tipo', 'status', 'created_at')
        list_filter = ('status',)
        search_fields = ('paciente__user__email',)
        readonly_fields = ('created_at',)
except Exception:
    pass
