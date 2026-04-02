"""
prescricao_app/views/receita_assinatura.py
View de assinatura digital via Gov.br.
A view é FINA — toda a lógica está em services/govbr_assinar_service.py.
"""
import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from trathea_core.utils.response import api_success, api_error, api_not_found, api_service_unavailable
from trathea_core.auth.permissions import IsDoctor, IsGovBrLinked
from trathea_core.signature.govbr_signature import GovBrSignatureError
from trathea_core.signature.govbr_oauth import GovBrTimeoutError

from prescricao_app.models import Receita
from prescricao_app.services.govbr_assinar_service import (
    GovBrAssinarService,
    ReceitaJaAssinadaError,
    ReceitaNaoPodeSerAssinadaError,
    MedicoNaoVinculadoError,
    AssinaturaError,
)

logger = logging.getLogger("trathea")

_assinar_service = GovBrAssinarService()


class ReceitaAssinarView(APIView):
    """
    POST /api/receitas/{id}/assinar/
    Assina a receita digitalmente via Gov.br (ICP-Brasil PAdES).

    Permissões: Médico proprietário da receita + conta Gov.br vinculada.

    Fluxo completo (delegado ao GovBrAssinarService):
    1. Validações de negócio (status, ownership, govbr_linked)
    2. Serialização canônica do conteúdo
    3. Geração do PDF
    4. Hash SHA-256 do PDF
    5. Envio do hash à API Gov.br → recebe PAdES
    6. Acoplamento PAdES ao PDF (modo dev: sem acoplamento)
    7. Salvamento e atualização de status
    8. Auditoria
    """

    permission_classes = [IsAuthenticated, IsDoctor]

    @extend_schema(
        tags=["Assinatura Digital"],
        summary="Assinar receita via Gov.br",
        description=(
            "Inicia o processo de assinatura digital ICP-Brasil via API Gov.br. "
            "O médico deve ter sua conta previamente vinculada ao Gov.br. "
            "Em caso de timeout do Gov.br, a receita permanece em rascunho."
        ),
        responses={
            200: OpenApiResponse(description="Receita assinada com sucesso."),
            400: OpenApiResponse(description="Receita já assinada ou status inválido."),
            402: OpenApiResponse(description="Médico não vinculou conta ao Gov.br."),
            403: OpenApiResponse(description="Acesso negado."),
            503: OpenApiResponse(description="Gov.br temporariamente indisponível."),
        },
    )
    def post(self, request, pk):
        # Buscar receita
        try:
            receita = Receita.objects.select_related(
                "medico__user", "paciente__user"
            ).prefetch_related("itens__medicamento").get(pk=pk)
        except Receita.DoesNotExist:
            return api_not_found("Receita não encontrada.")

        # Verificar ownership
        if receita.medico.user != request.user:
            return api_error(
                "Você não tem permissão para assinar esta receita.",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            resultado = _assinar_service.assinar_receita(receita=receita, request=request)

            return api_success(
                data=resultado,
                message="Receita assinada digitalmente com sucesso via Gov.br! "
                        "O paciente pode verificar a autenticidade pelo QR Code.",
            )

        except MedicoNaoVinculadoError as e:
            return api_error(
                str(e),
                http_status=status.HTTP_402_PAYMENT_REQUIRED,  # reutilizando 402 para "ação necessária"
            )

        except ReceitaJaAssinadaError as e:
            return api_error(str(e))

        except ReceitaNaoPodeSerAssinadaError as e:
            return api_error(str(e))

        except GovBrTimeoutError as e:
            return api_service_unavailable(str(e))

        except GovBrSignatureError as e:
            if getattr(e, "needs_reauth", False):
                return api_error(
                    str(e),
                    http_status=status.HTTP_401_UNAUTHORIZED,
                )
            return api_error(str(e), http_status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except AssinaturaError as e:
            logger.error(f"Assinatura error receita #{pk}: {e}", exc_info=True)
            return api_error(str(e))

        except Exception as e:
            logger.error(f"Erro inesperado assinatura receita #{pk}: {e}", exc_info=True)
            return api_error("Erro inesperado durante a assinatura. Contate o suporte.")
