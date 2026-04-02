"""admin_app/urls_solicitacoes.py — Rotas de solicitações de cadastro."""
from django.urls import path
from .views import SolicitacaoListView, SolicitacaoDetailView

urlpatterns = [
    path("", SolicitacaoListView.as_view(), name="solicitacao-list"),
    path("<int:pk>/", SolicitacaoDetailView.as_view(), name="solicitacao-detail"),
]
