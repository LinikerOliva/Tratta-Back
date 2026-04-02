"""
core_app/urls/user_urls.py
Rotas de perfil e configurações do usuário autenticado.
"""
from django.urls import path
from core_app.views.settings import my_profile_view, my_access_log_view, user_security_view

urlpatterns = [
    path("me/profile/",    my_profile_view,    name="user-profile"),
    path("me/access-log/", my_access_log_view, name="user-access-log"),
    path("me/security/",   user_security_view, name="user-security"),
]
