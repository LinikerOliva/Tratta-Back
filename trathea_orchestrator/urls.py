"""
TRATHEA — Gateway de URLs (Orquestrador)
Cada módulo registra suas rotas aqui. O Index actua como API Gateway.
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# ── Documentação OpenAPI ──────────────────────────────────────────────────────
schema_urls = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# ── Rotas da API ──────────────────────────────────────────────────────────────
api_urls = [
    # ── Core Auth & Usuários ───────────────────────────────────────────────
    path("auth/", include("core_app.urls.auth_urls")),
    path("users/", include("core_app.urls.user_urls")),

    # ── Módulo Médico ─────────────────────────────────────────────────────
    path("doctors/", include("medico_app.urls")),

    # ── Módulo Paciente ───────────────────────────────────────────────────
    path("patients/", include("paciente_app.urls")),
    path("prontuarios/", include("paciente_app.urls_prontuarios")),

    # ── Módulo Clínica ────────────────────────────────────────────────────
    path("clinics/", include("clinica_app.urls_clinica")),
    path("secretarias/", include("clinica_app.urls_secretaria")),

    # ── Módulo Consultas ──────────────────────────────────────────────────
    path("consultas/", include("consulta_app.urls_consultas")),
    path("agendamentos/", include("consulta_app.urls_agendamentos")),

    # ── Módulo Prescrição (Receitas) ──────────────────────────────────────
    path("receitas/", include("prescricao_app.urls_receitas")),
    path("medicamentos/", include("prescricao_app.urls_medicamentos")),

    # ── Módulo Exames ─────────────────────────────────────────────────────
    path("exames/", include("exame_app.urls")),

    # ── Módulo Admin ──────────────────────────────────────────────────────
    path("admin-panel/", include("admin_app.urls_admin")),
    path("solicitacoes/", include("admin_app.urls_solicitacoes")),

    # ── Core Trathea (IA, Auditoria, Busca) ──────────────────────────────
    path("ai/", include("trathea_core.ai.urls")),
    path("audit/", include("trathea_core.audit.urls")),
    path("search/", include("trathea_core.search.urls")),

    # ── OpenAPI Schema ────────────────────────────────────────────────────
    *schema_urls,
]

# ── URL Pública (sem autenticação) ────────────────────────────────────────────
public_urls = [
    # Verificação pública de receita por hash (QR Code)
    path("verificar/<str:hash_code>/", include("prescricao_app.urls_verificacao")),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include(api_urls)),
    path("", include(public_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
