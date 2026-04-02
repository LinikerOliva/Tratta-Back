"""admin_app/urls_admin.py — Rotas do painel admin."""
from django.urls import path
from .views import AdminDashboardView, AvaliarSolicitacaoView
from .views_usuarios import AdminUsuariosListView, AdminUsuarioDetailView
from .views_clinicas import AdminClinicasListView, AdminClinicaDetailView

urlpatterns = [
    path("", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("<int:pk>/avaliar/", AvaliarSolicitacaoView.as_view(), name="admin-avaliar"),
    
    # ── Usuários
    path("usuarios/", AdminUsuariosListView.as_view(), name="admin-usuarios"),
    path("usuarios/<int:pk>/", AdminUsuarioDetailView.as_view(), name="admin-usuario-detail"),
    
    # ── Clínicas
    path("clinicas/", AdminClinicasListView.as_view(), name="admin-clinicas"),
    path("clinicas/<int:pk>/", AdminClinicaDetailView.as_view(), name="admin-clinica-detail"),
]
