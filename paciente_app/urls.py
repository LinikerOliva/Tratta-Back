"""paciente_app/urls.py — Rotas de pacientes."""
from django.urls import path
from .views import PacienteListView, PacienteDetailView, MeuPerfilPacienteView
from .views_settings import paciente_health_data_view, paciente_preferences_view
from .views_prontuario_grid import (
    prontuario_grid_view,
    prontuario_especialidade_historico_view,
    minha_agenda_medicamentos_view,
    medicamento_checkin_view,
)
from .views_solicitacoes import (
    medicos_proximos_view,
    criar_solicitacao_view,
    minhas_solicitacoes_view,
)

urlpatterns = [
    path("", PacienteListView.as_view(), name="paciente-list"),
    path("me/", MeuPerfilPacienteView.as_view(), name="paciente-me"),
    path("<int:pk>/", PacienteDetailView.as_view(), name="paciente-detail"),
    # ── Configurações ────────────────────────────────────────────────
    path("me/health-data/",  paciente_health_data_view, name="paciente-health"),
    path("me/preferences/",  paciente_preferences_view, name="paciente-prefs"),
    # ── Grid de Especialidades (Prontuário) ──────────────────────────
    path("me/prontuario-grid/", prontuario_grid_view, name="prontuario-grid"),
    path("me/prontuario-grid/<str:especialidade>/", prontuario_especialidade_historico_view, name="prontuario-esp-historico"),
    # ── Agenda de Medicamentos ───────────────────────────────────────
    path("me/agenda-medicamentos/", minha_agenda_medicamentos_view, name="agenda-medicamentos"),
    path("me/medicamento-checkin/", medicamento_checkin_view, name="medicamento-checkin"),
    # ── Solicitação de Consulta ──────────────────────────────────────
    path("me/medicos-proximos/", medicos_proximos_view, name="medicos-proximos"),
    path("me/solicitacoes/", minhas_solicitacoes_view, name="solicitacoes-list"),
    path("me/solicitacoes/criar/", criar_solicitacao_view, name="solicitacoes-criar"),
]
