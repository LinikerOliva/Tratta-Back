"""exame_app/urls.py — Rotas de exames."""
from django.urls import path
from .views import TipoExameListView, SolicitacaoExameListView, SolicitacaoExameDetailView

urlpatterns = [
    path("tipos/", TipoExameListView.as_view(), name="tipo-exame-list"),
    path("", SolicitacaoExameListView.as_view(), name="exame-list"),
    path("<int:pk>/", SolicitacaoExameDetailView.as_view(), name="exame-detail"),
]
