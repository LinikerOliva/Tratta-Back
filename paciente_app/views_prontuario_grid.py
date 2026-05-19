"""
paciente_app/views_prontuario_grid.py
APIs para o Grid de Especialidades e Agenda de Medicamentos do paciente.
"""
import logging
import re
from datetime import timedelta

from django.db.models import Max, Prefetch
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error, api_not_found
from paciente_app.models import Paciente, Prontuario

logger = logging.getLogger("trathea")


def _resolve_paciente(user):
    """Resolve o Paciente do usuário autenticado."""
    if hasattr(user, "paciente"):
        return user.paciente
    return None


def _parse_intervalo_horas(posologia_text):
    """
    Tenta extrair o intervalo em horas de uma string de posologia.
    Ex: '8h em 8h' → 8, 'de 12 em 12 horas' → 12, '6/6h' → 6
    Fallback: 8 horas.
    """
    if not posologia_text:
        return 8

    text = posologia_text.lower().strip()

    # Padrão: "8h em 8h", "8 em 8 horas", "de 8 em 8h"
    match = re.search(r'(\d+)\s*h?\s*em\s*(\d+)', text)
    if match:
        return int(match.group(1))

    # Padrão: "6/6h", "12/12 horas"
    match = re.search(r'(\d+)\s*/\s*(\d+)', text)
    if match:
        return int(match.group(1))

    # Padrão: "a cada 8 horas", "a cada 6h"
    match = re.search(r'a cada\s+(\d+)', text)
    if match:
        return int(match.group(1))

    # Padrão: "1x ao dia" → 24h, "2x ao dia" → 12h, "3x ao dia" → 8h
    match = re.search(r'(\d+)\s*(?:x|vez)\s*(?:ao|por)\s*dia', text)
    if match:
        vezes = int(match.group(1))
        return max(1, 24 // vezes) if vezes > 0 else 24

    return 8  # fallback padrão


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. GRID DE ESPECIALIDADES (Prontuário)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@extend_schema(
    tags=["Portal Paciente"],
    summary="Grid de prontuários por especialidade",
    description=(
        "Retorna os prontuários do paciente autenticado agrupados por "
        "especialidade médica, exibindo apenas o registro mais recente de cada área."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prontuario_grid_view(request):
    """Grid de especialidades — último prontuário de cada área."""
    paciente = _resolve_paciente(request.user)
    if not paciente:
        return api_error("Perfil de paciente não encontrado.", http_status=404)

    prontuarios = (
        Prontuario.objects
        .filter(paciente=paciente)
        .select_related("medico__user", "medico")
        .order_by("-data_consulta")
    )

    # Agrupa por especialidade do médico
    especialidades = {}
    for p in prontuarios:
        esp = p.medico.especialidade if p.medico else "Geral"
        if esp not in especialidades:
            especialidades[esp] = {
                "especialidade": esp,
                "ultimo_registro": {
                    "id": p.id,
                    "data": p.data_consulta.isoformat() if p.data_consulta else None,
                    "medico": p.medico.user.nome_completo if p.medico else "—",
                    "diagnostico": p.hipotese_diagnostica or p.diagnostico_cid10 or "—",
                    "conduta": (p.conduta[:150] + "…") if p.conduta and len(p.conduta) > 150 else (p.conduta or "—"),
                    "queixa": p.queixa_principal or "—",
                    "cid10": p.diagnostico_cid10 or None,
                },
                "total_registros": 0,
            }
        especialidades[esp]["total_registros"] += 1

    return api_success(data=list(especialidades.values()))


@extend_schema(
    tags=["Portal Paciente"],
    summary="Histórico de uma especialidade",
    description="Retorna todos os prontuários do paciente de uma especialidade específica.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prontuario_especialidade_historico_view(request, especialidade):
    """Log completo de uma especialidade."""
    paciente = _resolve_paciente(request.user)
    if not paciente:
        return api_error("Perfil de paciente não encontrado.", http_status=404)

    prontuarios = (
        Prontuario.objects
        .filter(paciente=paciente, medico__especialidade__iexact=especialidade)
        .select_related("medico__user")
        .order_by("-data_consulta")
    )

    resultado = []
    for p in prontuarios:
        resultado.append({
            "id": p.id,
            "data": p.data_consulta.isoformat() if p.data_consulta else None,
            "medico": p.medico.user.nome_completo if p.medico else "—",
            "queixa": p.queixa_principal,
            "diagnostico": p.hipotese_diagnostica or "—",
            "conduta": p.conduta or "—",
            "cid10": p.diagnostico_cid10 or None,
            "anamnese": p.anamnese or "",
            "exame_fisico": getattr(p, "exame_fisico", "") or "",
        })

    return api_success(data={
        "especialidade": especialidade,
        "registros": resultado,
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. AGENDA DE MEDICAMENTOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@extend_schema(
    tags=["Portal Paciente"],
    summary="Agenda de medicamentos ativos",
    description=(
        "Lista os medicamentos da última receita válida do paciente, "
        "com cálculo do próximo horário de dose e status de adesão."
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def minha_agenda_medicamentos_view(request):
    """Medicamentos ativos com contagem regressiva e status."""
    from prescricao_app.models import Receita, MedicamentoCheckin

    paciente = _resolve_paciente(request.user)
    if not paciente:
        return api_error("Perfil de paciente não encontrado.", http_status=404)

    agora = timezone.now()

    # Busca receitas válidas (não expiradas, emitidas/assinadas)
    receitas_validas = (
        Receita.objects
        .filter(
            paciente=paciente,
            status__in=["emitida", "assinada", "enviada"],
        )
        .prefetch_related("itens__medicamento", "itens__checkins")
        .order_by("-data_emissao")
    )

    # Filtra manualmente as não expiradas
    receita_ativa = None
    for r in receitas_validas:
        if not r.esta_expirada:
            receita_ativa = r
            break

    if not receita_ativa:
        return api_success(data={
            "receita_id": None,
            "medicamentos": [],
            "mensagem": "Nenhuma receita ativa encontrada.",
        })

    medicamentos = []
    for item in receita_ativa.itens.all():
        intervalo_horas = _parse_intervalo_horas(item.posologia)
        data_inicio = receita_ativa.data_emissao

        # Calcula próxima dose
        horas_passadas = (agora - data_inicio).total_seconds() / 3600
        doses_tomadas_calculadas = int(horas_passadas // intervalo_horas)
        proxima_dose = data_inicio + timedelta(
            hours=(doses_tomadas_calculadas + 1) * intervalo_horas
        )

        # Verifica último check-in
        ultimo_checkin = (
            MedicamentoCheckin.objects
            .filter(item_receita=item, paciente=paciente)
            .order_by("-tomado_em")
            .first()
        )

        # Status da dose
        if ultimo_checkin and ultimo_checkin.tomado_em >= proxima_dose - timedelta(hours=intervalo_horas):
            status = "tomado"
        elif proxima_dose < agora:
            status = "atrasado"
        elif (proxima_dose - agora).total_seconds() <= 3600:
            status = "proximo"
        else:
            status = "aguardando"

        # Contagem total de checkins hoje
        checkins_hoje = (
            MedicamentoCheckin.objects
            .filter(
                item_receita=item,
                paciente=paciente,
                tomado_em__date=agora.date(),
            )
            .count()
        )

        medicamentos.append({
            "item_id": item.id,
            "nome": item.medicamento.nome if item.medicamento else "Medicamento",
            "principio_ativo": item.medicamento.principio_ativo if item.medicamento else "",
            "dosagem": item.dosagem,
            "posologia": item.posologia,
            "via": item.via_administracao or "oral",
            "duracao": item.duracao_tratamento or "—",
            "instrucoes": item.instrucoes_especiais or "",
            "intervalo_horas": intervalo_horas,
            "proxima_dose_iso": proxima_dose.isoformat(),
            "status": status,
            "checkins_hoje": checkins_hoje,
            "ultimo_checkin": ultimo_checkin.tomado_em.isoformat() if ultimo_checkin else None,
        })

    return api_success(data={
        "receita_id": receita_ativa.id,
        "data_emissao": receita_ativa.data_emissao.isoformat(),
        "validade_dias": receita_ativa.validade_dias,
        "medico": receita_ativa.medico.user.nome_completo if receita_ativa.medico else "—",
        "medicamentos": medicamentos,
    })


@extend_schema(
    tags=["Portal Paciente"],
    summary="Marcar medicamento como tomado",
    description="Registra o check-in de uma dose de medicamento.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def medicamento_checkin_view(request):
    """Registra check-in de dose."""
    from prescricao_app.models import ItemReceita, MedicamentoCheckin

    paciente = _resolve_paciente(request.user)
    if not paciente:
        return api_error("Perfil de paciente não encontrado.", http_status=404)

    item_id = request.data.get("item_id")
    if not item_id:
        return api_error("item_id é obrigatório.")

    try:
        item = ItemReceita.objects.select_related("receita").get(
            id=item_id, receita__paciente=paciente
        )
    except ItemReceita.DoesNotExist:
        return api_not_found("Item de receita não encontrado ou não pertence a este paciente.")

    # Evita check-in duplicado dentro de 30 min
    agora = timezone.now()
    recente = MedicamentoCheckin.objects.filter(
        item_receita=item,
        paciente=paciente,
        tomado_em__gte=agora - timedelta(minutes=30),
    ).exists()

    if recente:
        return api_error("Você já registrou esta dose recentemente. Aguarde pelo menos 30 minutos.")

    dose_ref = request.data.get("dose_referencia")
    checkin = MedicamentoCheckin.objects.create(
        item_receita=item,
        paciente=paciente,
        dose_referencia=dose_ref if dose_ref else None,
        observacao=request.data.get("observacao", ""),
    )

    logger.info(f"Check-in medicamento #{item_id} por paciente #{paciente.id}")

    return api_success(
        data={"checkin_id": checkin.id, "tomado_em": checkin.tomado_em.isoformat()},
        message="Dose registrada com sucesso! ✅",
    )
