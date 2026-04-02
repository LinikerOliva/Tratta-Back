"""paciente_app/urls.py — Rotas de pacientes."""
from django.urls import path
from .views import PacienteListView, PacienteDetailView, MeuPerfilPacienteView
from .views_settings import paciente_health_data_view, paciente_preferences_view

urlpatterns = [
    path("", PacienteListView.as_view(), name="paciente-list"),
    path("me/", MeuPerfilPacienteView.as_view(), name="paciente-me"),
    path("<int:pk>/", PacienteDetailView.as_view(), name="paciente-detail"),
    # ── Configurações ────────────────────────────────────────────────
    path("me/health-data/",  paciente_health_data_view, name="paciente-health"),
    path("me/preferences/",  paciente_preferences_view, name="paciente-prefs"),
]
