"""
prescricao_app/urls_receitas.py
Rotas do módulo de prescrições.
"""
from django.urls import path

from prescricao_app.views.receita_crud import ReceitaListCreateView, ReceitaDetailView
from prescricao_app.views.receita_assinatura import ReceitaAssinarView
from prescricao_app.views.receita_verificacao import verificar_receita_publica
from prescricao_app.views.receita_pdf import ReceitaPDFView

urlpatterns = [
    # ── CRUD ──────────────────────────────────────────────────────────────────
    path("", ReceitaListCreateView.as_view(), name="receita-list-create"),
    path("<int:pk>/", ReceitaDetailView.as_view(), name="receita-detail"),
    # ── Assinatura Digital Gov.br ──────────────────────────────────────────────
    path("<int:pk>/assinar/", ReceitaAssinarView.as_view(), name="receita-assinar"),
    # ── PDF ────────────────────────────────────────────────────────────────────
    path("<int:pk>/pdf/", ReceitaPDFView.as_view(), name="receita-pdf"),
]

# ── URL Pública de Verificação (montada no orquestrador como /verificar/{hash}/)
verificacao_urlpatterns = [
    path("", verificar_receita_publica, name="receita-verificar-publica"),
]
