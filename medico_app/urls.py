"""medico_app/urls.py — Rotas do módulo Médico."""
from django.urls import path
from .views import MedicoListView, MedicoDetailView, MeuPerfilMedicoView, MedicoDisponibilidadeView, MeusPacientesView
from .views_settings import medico_settings_view, medico_receituario_view, medico_agenda_view
from .views_consulta import carregar_contexto_paciente_view, calcular_dosagem_view, assinar_receita_govbr_view
from .views_paciente360 import (
    paciente_360_view,
    iniciar_consulta_inteligente_view,
    salvar_transcricao_view,
    estruturar_transcricao_ia_view,
    finalizar_consulta_completa_view,
    atendimento_detalhes_view
)

urlpatterns = [
    path("", MedicoListView.as_view(), name="medico-list"),
    path("me/", MeuPerfilMedicoView.as_view(), name="medico-me"),
    path("<int:pk>/", MedicoDetailView.as_view(), name="medico-detail"),
    path("<int:pk>/agenda/", MedicoDisponibilidadeView.as_view(), name="medico-agenda"),
    # ── Configurações ──────────────────────────────────────────────────────────
    path("me/pacientes/",   MeusPacientesView.as_view(), name="medico-meus-pacientes"),
    path("me/settings/",    medico_settings_view,    name="medico-settings"),
    path("me/receituario/", medico_receituario_view, name="medico-receituario"),
    path("me/agenda/",      medico_agenda_view,      name="medico-agenda-config"),
    
    # ── Iniciar Consulta / Receita Inteligente ─────────────────────────────────
    path("consulta/contexto/<int:paciente_id>/", carregar_contexto_paciente_view, name="consulta-contexto"),
    path("consulta/smart-rx/", calcular_dosagem_view, name="consulta-smart-rx"),
    path("consulta/assinar-govbr/", assinar_receita_govbr_view, name="consulta-assinar-govbr"),

    # ── Jornada do Médico: Dashboard 360° e Consulta Inteligente ───────────────
    path("paciente-360/<int:paciente_id>/", paciente_360_view, name="paciente-360"),
    path("consulta-inteligente/iniciar/", iniciar_consulta_inteligente_view, name="consulta-inteligente-iniciar"),
    path("consulta-inteligente/<int:consulta_id>/transcricao/", salvar_transcricao_view, name="consulta-transcricao"),
    path("consulta-inteligente/<int:consulta_id>/estruturar-ia/", estruturar_transcricao_ia_view, name="consulta-estruturar-ia"),
    path("consulta-inteligente/<int:consulta_id>/finalizar/", finalizar_consulta_completa_view, name="consulta-finalizar-completa"),
    path("atendimento/<int:atendimento_id>/detalhes/", atendimento_detalhes_view, name="atendimento-detalhes"),
]
