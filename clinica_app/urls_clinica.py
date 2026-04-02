"""clinica_app/urls_clinica.py — Rotas de clínicas."""
from django.urls import path
from .views import ClinicaListView, ClinicaDetailView, MinhaClinicaView, ClinicaAdicionarMedicoView
from .views_settings import clinica_settings_view, clinica_triagem_view, clinica_rbac_view

urlpatterns = [
    path("", ClinicaListView.as_view(), name="clinica-list"),
    path("me/", MinhaClinicaView.as_view(), name="clinica-me"),
    path("<int:pk>/", ClinicaDetailView.as_view(), name="clinica-detail"),
    path("<int:pk>/medicos/", ClinicaAdicionarMedicoView.as_view(), name="clinica-add-medico"),
    # ── Configurações ─────────────────────────────────────────────────────────
    path("me/settings/",  clinica_settings_view, name="clinica-settings"),
    path("me/triagem/",   clinica_triagem_view,  name="clinica-triagem"),
    path("me/rbac/",      clinica_rbac_view,     name="clinica-rbac"),
]
