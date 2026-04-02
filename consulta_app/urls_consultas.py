"""consulta_app/urls_consultas.py — Rotas de consultas."""
from django.urls import path
from .views import ConsultaListView, ConsultaDetailView

urlpatterns = [
    path("", ConsultaListView.as_view(), name="consulta-list"),
    path("<int:pk>/", ConsultaDetailView.as_view(), name="consulta-detail"),
]
