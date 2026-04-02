"""
prescricao_app/urls_verificacao.py
URL pública de verificação de receitas por hash (QR Code).
"""
from django.urls import path
from prescricao_app.views.receita_verificacao import verificar_receita_publica

urlpatterns = [
    path("", verificar_receita_publica, name="receita-verificar-publica"),
]
