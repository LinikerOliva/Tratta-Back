"""consulta_app/urls_agendamentos.py — Rotas de agendamentos."""
from django.urls import path
from .views import AgendamentoListView, AgendamentoDetailView

urlpatterns = [
    path("", AgendamentoListView.as_view(), name="agendamento-list"),
    path("<int:pk>/", AgendamentoDetailView.as_view(), name="agendamento-detail"),
]
