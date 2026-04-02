"""paciente_app/urls_prontuarios.py — Rotas de prontuários."""
from django.urls import path
from .views import ProntuarioListView, ProntuarioDetailView

urlpatterns = [
    path("", ProntuarioListView.as_view(), name="prontuario-list"),
    path("<int:pk>/", ProntuarioDetailView.as_view(), name="prontuario-detail"),
]
