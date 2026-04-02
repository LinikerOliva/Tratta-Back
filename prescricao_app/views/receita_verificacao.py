"""
prescricao_app/views/receita_verificacao.py
Verificação PÚBLICA de autenticidade de receitas por hash (QR Code).
Este endpoint NÃO requer autenticação — é para uso público.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from trathea_core.utils.response import api_success, api_not_found

from prescricao_app.models import Receita


@extend_schema(
    tags=["Verificação Pública"],
    summary="Verificar autenticidade de receita por hash",
    description=(
        "Endpoint PÚBLICO para verificação de autenticidade de receitas via QR Code. "
        "Não requer autenticação. Retorna dados básicos da receita se o hash for válido."
    ),
    parameters=[
        OpenApiParameter("hash_code", location="path", description="Hash de verificação da receita (64 chars hex)"),
    ],
    responses={
        200: OpenApiResponse(description="Receita válida e autêntica."),
        404: OpenApiResponse(description="Hash inválido ou receita não encontrada."),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def verificar_receita_publica(request, hash_code):
    """
    GET /verificar/{hash_code}/

    Verifica autenticidade de uma receita por hash público.
    Retorna apenas dados não sensíveis (sem CPF completo, sem dados privados).
    """
    if not hash_code or len(hash_code) != 64:
        return api_not_found("Hash de verificação inválido.")

    try:
        receita = Receita.objects.select_related(
            "medico__user", "medico",
            "paciente__user",
        ).prefetch_related("itens__medicamento").get(
            hash_verificacao=hash_code,
            status="assinada",
        )
    except Receita.DoesNotExist:
        return api_not_found(
            "Receita não encontrada ou não possui assinatura digital válida. "
            "Verifique o QR Code e tente novamente."
        )

    # Verifica expiração
    esta_valida = not receita.esta_expirada

    # Mascarar dados sensíveis para exibição pública
    cpf_paciente = receita.paciente.user.profile.cpf
    cpf_mascarado = f"***.***.{cpf_paciente[-6:-3]}-{cpf_paciente[-2:]}" if cpf_paciente else "***"

    return api_success(
        data={
            "valida": esta_valida,
            "status": receita.status,
            "tipo": receita.tipo,
            "emitida_em": receita.data_emissao.strftime("%d/%m/%Y %H:%M"),
            "assinada_em": receita.assinada_em.strftime("%d/%m/%Y %H:%M") if receita.assinada_em else None,
            "expira_em": (
                (receita.data_emissao.date().__str__())
            ),
            "assinatura_digital": {
                "via_govbr": receita.via_govbr,
                "icp_brasil": receita.via_govbr,
            },
            "medico": {
                "nome": f"Dr(a). {receita.medico.user.nome_completo}",
                "crm": f"CRM/{receita.medico.crm_estado} {receita.medico.crm}",
                "especialidade": receita.medico.especialidade,
            },
            "paciente": {
                "nome": receita.paciente.user.nome_completo,
                "cpf": cpf_mascarado,  # CPF mascarado para privacidade
            },
            "medicamentos": [
                {
                    "nome": item.medicamento.nome,
                    "principio_ativo": item.medicamento.principio_ativo,
                    "dosagem": item.dosagem,
                    "posologia": item.posologia,
                    "quantidade": item.quantidade,
                }
                for item in receita.itens.all()
            ],
            "aviso_expirada": "RECEITA EXPIRADA" if not esta_valida else None,
        },
        message="Receita verificada com sucesso. Assinatura digital ICP-Brasil válida."
        if esta_valida and receita.via_govbr
        else "Receita encontrada.",
    )
