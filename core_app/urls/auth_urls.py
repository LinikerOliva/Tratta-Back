"""
core_app/urls/auth_urls.py
Rotas de autenticação e Gov.br.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from core_app.views.auth import (
    login_view,
    logout_view,
    me_view,
    register_view,
    register_medico_view,
    register_clinica_view,
    change_password_view,
    govbr_authorize_view,
    govbr_callback_view,
)

urlpatterns = [
    # JWT
    path("login/", login_view, name="auth-login"),
    path("logout/", logout_view, name="auth-logout"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", me_view, name="auth-me"),
    # Cadastro
    path("register/", register_view, name="auth-register"),
    path("register/medico/", register_medico_view, name="auth-register-medico"),
    path("register/clinica/", register_clinica_view, name="auth-register-clinica"),
    path("change-password/", change_password_view, name="auth-change-password"),
    # Gov.br OAuth2
    path("govbr/authorize/", govbr_authorize_view, name="govbr-authorize"),
    path("govbr/callback/", govbr_callback_view, name="govbr-callback"),
]
