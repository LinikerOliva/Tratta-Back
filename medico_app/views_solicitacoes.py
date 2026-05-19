"""
medico_app/views_solicitacoes.py
Views para o médico gerenciar e responder as solicitações de consulta feitas pelos pacientes.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.db import models

from trathea_core.utils.response import api_success, api_error
from paciente_app.models import SolicitacaoConsulta

@extend_schema(
    tags=["Médico - Solicitações"],
    summary="Listar solicitações recebidas pelo médico",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def medico_solicitacoes_list_view(request):
    """
    GET /api/medicos/me/solicitacoes/
    Retorna as solicitações de consulta enviadas pacientes para este médico.
    """
    if request.user.role != "medico":
        return api_error("Acesso negado", status.HTTP_403_FORBIDDEN)

    medico = getattr(request.user, "medico", None)
    if not medico:
        return api_success(data=[])

    # Ordena: Pendentes primeiro, mais recentes primeiro
    solicitacoes = SolicitacaoConsulta.objects.filter(medico=medico).order_by(
        models.Case(
            models.When(status="pendente", then=0),
            default=1,
            output_field=models.IntegerField(),
        ),
        "-created_at"
    )

    data = []
    for s in solicitacoes:
        foto_url = None
        if hasattr(s.paciente.user, "profile") and s.paciente.user.profile.foto:
            foto_url = request.build_absolute_uri(s.paciente.user.profile.foto.url)
            
        data.append({
            "id": s.id,
            "paciente_nome": s.paciente.user.nome_completo,
            "paciente_foto_url": foto_url,
            "data_preferencia": str(s.data_preferencia),
            "periodo_preferencia": s.get_periodo_preferencia_display(),
            "motivo": s.motivo,
            "status": s.status,
            "status_display": s.get_status_display(),
            "resposta_clinica": s.resposta_clinica,
            "criado_em": str(s.created_at)
        })

    return api_success(data=data)


@extend_schema(
    tags=["Médico - Solicitações"],
    summary="Responder a uma solicitação de consulta",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def responder_solicitacao_view(request, solicitacao_id):
    """
    POST /api/medicos/me/solicitacoes/<id>/responder/
    {
       "status": "aceita" (ou recusada, novo_horario)
       "resposta_clinica": "Agendado para 10:30 do dia solcitado"
    }
    """
    if request.user.role != "medico":
        return api_error("Acesso negado", status.HTTP_403_FORBIDDEN)

    medico = getattr(request.user, "medico", None)
    
    try:
        solicitacao = SolicitacaoConsulta.objects.get(id=solicitacao_id, medico=medico)
    except SolicitacaoConsulta.DoesNotExist:
        return api_error("Solicitação não encontrada", status.HTTP_404_NOT_FOUND)

    novo_status = request.data.get("status")
    resposta = request.data.get("resposta_clinica", "")

    if novo_status not in [choice[0] for choice in SolicitacaoConsulta.Status.choices]:
        return api_error("Status inválido", status.HTTP_400_BAD_REQUEST)

    solicitacao.status = novo_status
    solicitacao.resposta_clinica = resposta
    solicitacao.save()

    return api_success(message="Resposta enviada ao paciente com sucesso!")
