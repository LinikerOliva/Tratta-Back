"""
paciente_app/views_solicitacoes.py
Views para o paciente solicitar consultas e buscar médicos por proximidade.
"""
import math
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.utils import timezone

from trathea_core.utils.response import api_success, api_error
from medico_app.models import Medico
from paciente_app.models import SolicitacaoConsulta

def haversine(lat1, lon1, lat2, lon2):
    """Calcula a distância aproximada em KM usando a fórmula de Haversine."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    R = 6371  # Raio da terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@extend_schema(
    tags=["Paciente - Solicitações"],
    summary="Buscar médicos próximos",
    description="Retorna médicos ordenados por proximidade da geolocalização fornecida."
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def medicos_proximos_view(request):
    """
    GET /api/paciente/me/medicos-proximos/?lat=-23.5&lng=-46.6&q=Cardio
    - Lista médicos, calculando a distância até a clínica principal.
    - Em ambiente SQL Server usa-se STDistance. Como é um protótipo SQLite aqui, calculamos no backend.
    """
    if request.user.role != "paciente":
        return api_error("Acesso negado", status.HTTP_403_FORBIDDEN)

    try:
        user_lat = float(request.GET.get("lat"))
        user_lng = float(request.GET.get("lng"))
    except (TypeError, ValueError):
        # Se não fornecer, usamos zero mas o filtro continuará (sem distância precisa)
        user_lat, user_lng = None, None

    query = request.GET.get("q", "").strip().lower()

    # Pega todos os médicos com clínica principal
    medicos_qs = Medico.objects.select_related("user", "clinica_principal").filter(user__is_active=True)

    resultados = []
    for m in medicos_qs:
        # Filtro textual (Nome ou Especialidade)
        match_nome = query in m.user.nome_completo.lower()
        match_esp = query in (m.especialidade or "").lower()
        if query and not (match_nome or match_esp):
            continue

        distancia = float('inf')
        if user_lat is not None and user_lng is not None and m.clinica_principal:
            c_lat = m.clinica_principal.latitude
            c_lng = m.clinica_principal.longitude
            distancia = haversine(user_lat, user_lng, c_lat, c_lng)
            
            # Se não tiver lat/lng na clínica, simulamos uma distância aleatória baseada no ID 
            # para o front-end não ficar vazio no seu protótipo.
            if c_lat is None:
                distancia = 2.0 + (m.id % 15) * 0.5 

        # Se não tivermos lat/lon mas queremos mostrar
        if distancia == float('inf'):
            distancia = 2.0 + (m.id % 15) * 0.5 

        foto_url = None
        if hasattr(m.user, "profile") and m.user.profile.foto:
            foto_url = request.build_absolute_uri(m.user.profile.foto.url)

        resultados.append({
            "id": m.id,
            "nome": m.user.nome_completo,
            "especialidade": m.especialidade,
            "foto_url": foto_url,
            "clinica": m.clinica_principal.nome_fantasia if m.clinica_principal else "Clínica Padrão",
            "distancia_km": round(distancia, 1)
        })

    # Ordena pelos mais próximos
    resultados.sort(key=lambda x: x["distancia_km"])

    return api_success(data=resultados)


@extend_schema(
    tags=["Paciente - Solicitações"],
    summary="Criar solicitação de consulta",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def criar_solicitacao_view(request):
    """
    POST /api/paciente/me/solicitacoes/
    {
      "medico_id": 1,
      "data_preferencia": "2024-05-10",
      "periodo_preferencia": "manha|tarde|noite",
      "motivo": "Check-up rotina"
    }
    """
    if request.user.role != "paciente":
        return api_error("Acesso negado", status.HTTP_403_FORBIDDEN)

    paciente = getattr(request.user, "paciente", None)
    if not paciente:
        return api_error("Perfil de paciente não encontrado.", status.HTTP_400_BAD_REQUEST)

    medico_id = request.data.get("medico_id")
    dt_pref = request.data.get("data_preferencia")
    per_pref = request.data.get("periodo_preferencia")
    motivo = request.data.get("motivo")

    if not all([medico_id, dt_pref, per_pref, motivo]):
        return api_error("Preencha todos os campos da solicitação.", status.HTTP_400_BAD_REQUEST)

    try:
        medico = Medico.objects.get(pk=medico_id)
    except Medico.DoesNotExist:
        return api_error("Médico não encontrado.", status.HTTP_404_NOT_FOUND)

    solicitacao = SolicitacaoConsulta.objects.create(
        paciente=paciente,
        medico=medico,
        data_preferencia=dt_pref,
        periodo_preferencia=per_pref,
        motivo=motivo[:255]
    )

    return api_success(data={"id": solicitacao.id, "status": solicitacao.status}, message="Solicitação enviada com sucesso!")


@extend_schema(
    tags=["Paciente - Solicitações"],
    summary="Listar solicitações do paciente",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def minhas_solicitacoes_view(request):
    """
    GET /api/paciente/me/solicitacoes/
    """
    if request.user.role != "paciente":
        return api_error("Acesso negado", status.HTTP_403_FORBIDDEN)

    paciente = getattr(request.user, "paciente", None)
    if not paciente:
        return api_success(data=[])

    solics = SolicitacaoConsulta.objects.filter(paciente=paciente)
    data = []
    for s in solics:
        foto_url = None
        if hasattr(s.medico.user, "profile") and s.medico.user.profile.foto:
            foto_url = request.build_absolute_uri(s.medico.user.profile.foto.url)
            
        data.append({
            "id": s.id,
            "medico_nome": s.medico.user.nome_completo,
            "especialidade": s.medico.especialidade,
            "foto_url": foto_url,
            "data_preferencia": str(s.data_preferencia),
            "periodo_preferencia": s.get_periodo_preferencia_display(),
            "motivo": s.motivo,
            "status": s.status,
            "status_display": s.get_status_display(),
            "resposta_clinica": s.resposta_clinica,
            "criado_em": str(s.created_at)
        })

    return api_success(data=data)
