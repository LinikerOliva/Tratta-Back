"""
admin_app/views.py
Views do módulo Admin — gerenciamento de solicitações de cadastro.
"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from trathea_core.utils.response import api_success, api_error, api_not_found, api_created
from trathea_core.auth.permissions import IsAdminUser

from .models import SolicitacaoCadastro
from .serializers import (
    SolicitacaoCadastroSerializer,
    SolicitacaoCadastroCreateSerializer,
    AvaliarSolicitacaoSerializer,
)

logger = logging.getLogger("trathea")


class SolicitacaoListView(APIView):
    """
    GET /api/solicitacoes/  — Admin vê todas; usuário comum vê as suas.
    POST /api/solicitacoes/ — Qualquer usuário autenticado cria uma solicitação.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Admin"], summary="Listar solicitações de cadastro")
    def get(self, request):
        if request.user.role == "admin":
            qs = SolicitacaoCadastro.objects.select_related(
                "solicitante", "avaliado_por"
            ).all()
            status_param = request.query_params.get("status")
            tipo_param = request.query_params.get("tipo")
            if status_param:
                qs = qs.filter(status=status_param)
            if tipo_param:
                qs = qs.filter(tipo=tipo_param)
        else:
            qs = SolicitacaoCadastro.objects.filter(solicitante=request.user)
        serializer = SolicitacaoCadastroSerializer(qs, many=True)
        return api_success(data=serializer.data)

    @extend_schema(tags=["Admin"], summary="Criar solicitação de cadastro")
    def post(self, request):
        serializer = SolicitacaoCadastroCreateSerializer(data=request.data)
        if serializer.is_valid():
            solicitacao = serializer.save(solicitante=request.user)
            return api_created(
                data=SolicitacaoCadastroSerializer(solicitacao).data,
                message="Solicitação enviada com sucesso. Aguarde a análise do administrador.",
            )
        return api_error("Dados inválidos.", errors=serializer.errors)


class SolicitacaoDetailView(APIView):
    """GET /api/solicitacoes/<pk>/ — Detalhes da solicitação."""

    permission_classes = [IsAuthenticated]

    def _get_solicitacao(self, pk, user):
        try:
            qs = SolicitacaoCadastro.objects.select_related("solicitante", "avaliado_por")
            if user.role != "admin":
                qs = qs.filter(solicitante=user)
            return qs.get(pk=pk)
        except SolicitacaoCadastro.DoesNotExist:
            return None

    @extend_schema(tags=["Admin"], summary="Detalhes da solicitação")
    def get(self, request, pk):
        solicitacao = self._get_solicitacao(pk, request.user)
        if not solicitacao:
            return api_not_found("Solicitação não encontrada.")
        serializer = SolicitacaoCadastroSerializer(solicitacao)
        return api_success(data=serializer.data)


class AvaliarSolicitacaoView(APIView):
    """
    POST /api/admin-panel/<pk>/avaliar/
    Admin aprova ou rejeita uma solicitação de cadastro.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Avaliar solicitação (aprovar/rejeitar)")
    def post(self, request, pk):
        try:
            solicitacao = SolicitacaoCadastro.objects.select_related("solicitante").get(pk=pk)
        except SolicitacaoCadastro.DoesNotExist:
            return api_not_found("Solicitação não encontrada.")

        if solicitacao.status in ("aprovada", "rejeitada"):
            return api_error(
                f"Esta solicitação já foi {solicitacao.status}. Não é possível reavaliá-la."
            )

        serializer = AvaliarSolicitacaoSerializer(data=request.data)
        if not serializer.is_valid():
            return api_error("Dados inválidos.", errors=serializer.errors)

        novo_status = serializer.validated_data["status"]
        motivo = serializer.validated_data.get("motivo_rejeicao", "")

        solicitacao.status = novo_status
        solicitacao.avaliado_por = request.user
        solicitacao.motivo_rejeicao = motivo
        solicitacao.save(update_fields=["status", "avaliado_por", "motivo_rejeicao", "updated_at"])

        from core_app.models import CustomUser
        if novo_status == "aprovada":
            user = solicitacao.solicitante
            dados = solicitacao.dados_adicionais or {}
            
            if solicitacao.tipo == "medico":
                from medico_app.models import Medico
                user.role = CustomUser.Role.MEDICO
                user.save(update_fields=["role"])
                
                if not hasattr(user, "medico"):
                    Medico.objects.create(
                        user=user,
                        crm=dados.get("crm", "000000"),
                        crm_estado=dados.get("crm_estado", "SP"),
                        especialidade=dados.get("especialidade", "Clínica Médica"),
                        rqe=dados.get("rqe", ""),
                        bio=dados.get("motivacao", "")
                    )
            elif solicitacao.tipo == "clinica":
                from clinica_app.models import Clinica
                user.role = CustomUser.Role.CLINICA
                user.save(update_fields=["role"])
                
                if not hasattr(user, "clinica"):
                    Clinica.objects.create(
                        user=user,
                        cnpj=dados.get("cnpj", "00000000000000"),
                        nome_fantasia=user.nome_completo,
                        telefone=dados.get("telefone", ""),
                        endereco_logradouro=dados.get("endereco", "")
                    )

        # Envio de E-mail Automático (Feedback Proativo)
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            nome_medico = solicitacao.solicitante.nome_completo
            email_medico = solicitacao.solicitante.email
            
            if novo_status == "aprovada":
                assunto = "Trathea - Cadastro Aprovado!"
                mensagem = f"Olá, Dr(a) {nome_medico}!\n\n" \
                           f"Seu cadastro no Trathea foi aprovado com sucesso.\n\n" \
                           f"Agora você já pode acessar o painel, configurar seu receituário e realizar consultas inteligentes.\n\n" \
                           f"Acesse agora: https://trathea.com.br/login\n\n" \
                           f"Atenciosamente,\nEquipe Trathea"
            else:
                assunto = "Trathea - Atualização sobre seu cadastro"
                mensagem = f"Olá, {nome_medico}.\n\n" \
                           f"Infelizmente sua solicitação não foi aprovada pelo seguinte motivo:\n\n" \
                           f"Motivo: {motivo}\n\n" \
                           f"Por favor, realize os ajustes necessários no seu perfil ou entre em contato com o suporte para uma nova análise.\n\n" \
                           f"Atenciosamente,\nEquipe Trathea"
                           
            send_mail(
                subject=assunto,
                message=mensagem,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'no-reply@trathea.com.br',
                recipient_list=[email_medico],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de decissao do admin: {str(e)}")

        acao = "aprovada" if novo_status == "aprovada" else "rejeitada"
        logger.info(
            f"Solicitação #{pk} {acao} pelo admin {request.user.email}"
        )

        return api_success(
            data=SolicitacaoCadastroSerializer(solicitacao).data,
            message=f"Solicitação {acao} com sucesso.",
        )


class AdminDashboardView(APIView):
    """GET /api/admin-panel/ — Dashboard com resumo do sistema."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=["Admin"], summary="Dashboard administrativo")
    def get(self, request):
        from core_app.models import CustomUser
        from medico_app.models import Medico
        from paciente_app.models import Paciente
        from clinica_app.models import Clinica

        pendentes = SolicitacaoCadastro.objects.filter(status="pendente").count()
        em_analise = SolicitacaoCadastro.objects.filter(status="em_analise").count()

        data = {
            "totais": {
                "usuarios": CustomUser.objects.count(),
                "medicos": Medico.objects.count(),
                "pacientes": Paciente.objects.count(),
                "clinicas": Clinica.objects.count(),
            },
            "solicitacoes": {
                "pendentes": pendentes,
                "em_analise": em_analise,
                "total_abertas": pendentes + em_analise,
            },
        }
        return api_success(data=data, message="Dashboard carregado com sucesso.")
