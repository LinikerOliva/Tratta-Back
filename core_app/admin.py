"""
core_app/admin.py
Registro dos modelos de autenticação no Django Admin.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil'
    extra = 0
    fields = ('cpf', 'telefone', 'data_nascimento', 'genero', 'foto',
              'endereco_logradouro', 'endereco_numero', 'endereco_cidade',
              'endereco_estado', 'endereco_cep')


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
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
    filter_horizontal = ('groups', 'user_permissions')
