"""clinica_app/urls_secretaria.py — Rotas de secretarias."""
from django.urls import path
from .views import SecretariaListView, SecretariaDetailView

urlpatterns = [
    path("", SecretariaListView.as_view(), name="secretaria-list"),
    path("<int:pk>/", SecretariaDetailView.as_view(), name="secretaria-detail"),
]
