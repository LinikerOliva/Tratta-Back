"""
core_app/views/auth.py
Views de autenticação — login, logout, register, me, change-password, Gov.br.

Todos os endpoints seguem o padrão:
    {"success": bool, "data": {}, "message": "...", "errors": []}
"""
import logging

from django.contrib.auth import update_session_auth_hash
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from trathea_core.utils.response import api_success, api_created, api_error, api_service_unavailable
from trathea_core.audit.audit import log_audit
from trathea_core.audit.models import LogAuditoria
from trathea_core.signature.govbr_oauth import GovBrOAuthService, GovBrAuthError, GovBrTimeoutError
from trathea_core.auth.permissions import IsDoctor

from core_app.models import CustomUser
from core_app.serializers import (
    CustomTokenObtainPairSerializer,
    CustomUserSerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
)
from admin_app.models import SolicitacaoCadastro

logger = logging.getLogger("trathea")

govbr_service = GovBrOAuthService()


# ── Login ─────────────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Login de usuário",
    description="Autentica o usuário e retorna tokens JWT (access + refresh).",
    responses={
        200: OpenApiResponse(description="Login realizado com sucesso."),
        401: OpenApiResponse(description="Credenciais inválidas."),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def login_view(request):
    """
    POST /api/auth/login/

    Body: { "email": "...", "password": "..." }
    """
    serializer = CustomTokenObtainPairSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        return api_error(
            message="Credenciais inválidas.",
            errors=serializer.errors,
            http_status=status.HTTP_401_UNAUTHORIZED,
        )

    user = CustomUser.objects.get(email=request.data.get("email", "").lower())
    log_audit(request, LogAuditoria.Acao.LOGIN, modelo="CustomUser", pk_objeto=str(user.id))

    return api_success(
        data={
            "access": serializer.validated_data["access"],
            "refresh": serializer.validated_data["refresh"],
            "user": CustomUserSerializer(user).data,
        },
        message=f"Bem-vindo, {user.nome_completo}!",
    )


# ── Logout ────────────────────────────────────────────────────────────────────
@extend_schema(tags=["Auth"], summary="Logout — invalida o refresh token")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    POST /api/auth/logout/

    Body: { "refresh": "..." }
    """
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return api_error("Token de refresh não fornecido.")

        token = RefreshToken(refresh_token)
        token.blacklist()

        log_audit(request, LogAuditoria.Acao.LOGOUT)

        return api_success(message="Logout realizado com sucesso.")

    except Exception as e:
        logger.warning(f"Logout error: {e}")
        return api_error("Token inválido ou já expirado.")


# ── Me ────────────────────────────────────────────────────────────────────────
@extend_schema(tags=["Auth"], summary="Dados do usuário autenticado")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """GET /api/auth/me/"""
    serializer = CustomUserSerializer(request.user)
    return api_success(data=serializer.data)


# ── Register ──────────────────────────────────────────────────────────────────
@extend_schema(tags=["Auth"], summary="Cadastro de novo usuário")
@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """
    POST /api/auth/register/

    Body: { email, nome_completo, role, password, password_confirm, cpf }
    """
    serializer = RegisterSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        return api_error(
            message="Dados inválidos. Verifique os campos.",
            errors=serializer.errors,
        )

    user = serializer.save()
    return api_created(
        data={"user_id": user.id, "email": user.email, "role": user.role},
        message="Cadastro realizado com sucesso! Verifique seu email para ativar a conta.",
    )


# ── Register Médico (com aprovação) ───────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Cadastro de médico — requer aprovação do admin",
    description=(
        "Cria a conta com role='paciente' temporariamente e abre uma "
        "SolicitacaoCadastro para o admin analisar. Aceita multipart/form-data "
        "para envio de documentos (diploma, CRM, etc.)."
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_medico_view(request):
    """
    POST /api/auth/register/medico/

    Body (multipart/form-data):
        nome_completo, email, password, password_confirm, cpf,
        crm, especialidade, instituicao_formacao,
        [diplomaMedicina, certificadoResidencia, comprovanteExperiencia]
    """
    # 1. Validações prévias e Consulta Automática via API do CFM (O "Pulo do Gato")
    data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
    crm = data.get("crm", "")
    uf = data.get("crm_estado", "SP")  # Adiciona uf caso chegue
    nome_digitado = data.get("nome_completo", "")

    # Invoca mock da integração CFM
    from trathea_core.services.crm_service import consultar_cfm_mock
    from rest_framework import status
    from django.utils import timezone

    cfm_data = consultar_cfm_mock(crm, uf, nome_digitado)
    
    if cfm_data["status"] in ["Inativo", "Inexistente"]:
        return api_error(
            message=f"Cadastro não aprovado. O CRM consta como {cfm_data['status']} no Conselho de Medicina.",
            http_status=status.HTTP_400_BAD_REQUEST,
            errors={"crm": f"Status: {cfm_data['status']}"}
        )

    # Monta payload com role=paciente para criar a conta base (Aguarda Verificação)
    data["role"] = "paciente"
    data["password_confirm"] = data.get("password_confirm") or data.get("password", "")

    serializer = RegisterSerializer(data=data, context={"request": request})
    if not serializer.is_valid():
        return api_error(
            message="Dados inválidos. Verifique os campos.",
            errors=serializer.errors,
        )

    user = serializer.save()

    # Monta dados adicionais da solicitação incluindo retorno da validação
    dados = {
        "crm": crm,
        "crm_estado": uf,
        "especialidade": data.get("especialidade", ""),
        "rqe": data.get("rqe", cfm_data.get("rqe", "")), # Captamos do CFM ou digitado
        "instituicao_formacao": data.get("instituicao_formacao", ""),
        "ano_formacao": data.get("ano_formacao", ""),
        "residencia": data.get("residencia", ""),
        "ano_residencia": data.get("ano_residencia", ""),
        "experiencia": data.get("experiencia", ""),
        "motivacao": data.get("motivacao", ""),
        "telefone": data.get("telefone", ""),
        # Audit details para Admin ver no Dashboard
        "nome_digitado": nome_digitado,
        "nome_oficial_cfm": cfm_data.get("nome_oficial"),
        "crm_status": cfm_data.get("status"),
        "data_validacao": timezone.now().isoformat()
    }

    # Documento principal (diploma ou primeiro enviado)
    doc = (
        request.FILES.get("diplomaMedicina")
        or request.FILES.get("certificadoResidencia")
        or request.FILES.get("comprovanteExperiencia")
    )

    SolicitacaoCadastro.objects.create(
        solicitante=user,
        tipo=SolicitacaoCadastro.Tipo.MEDICO,
        dados_adicionais=dados,
        documento_comprobatorio=doc,
    )

    log_audit(request, LogAuditoria.Acao.CRIAR, modelo="CustomUser", pk_objeto=str(user.id))

    return api_created(
        data={"user_id": user.id, "email": user.email, "role": "paciente", "pendente_aprovacao": True},
        message="Conta criada! Você já pode acessar como Paciente enquanto sua solicitação de Médico é analisada (2–5 dias úteis).",
    )


# ── Register Clínica (com aprovação) ──────────────────────────────────────────
@extend_schema(
    tags=["Auth"],
    summary="Cadastro de clínica — requer aprovação do admin",
    description=(
        "Cria a conta com role='paciente' temporariamente e abre uma "
        "SolicitacaoCadastro para o admin analisar. Aceita multipart/form-data "
        "para envio de documentos (contrato social, alvará, etc.)."
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_clinica_view(request):
    """
    POST /api/auth/register/clinica/

    Body (multipart/form-data):
        nome_completo, email, password, password_confirm, cpf,
        cnpj, endereco, especialidade,
        [contratoSocial, alvaraFuncionamento, crmClinica]
    """
    data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
    data["role"] = "paciente"
    data["password_confirm"] = data.get("password_confirm") or data.get("password", "")

    serializer = RegisterSerializer(data=data, context={"request": request})
    if not serializer.is_valid():
        return api_error(
            message="Dados inválidos. Verifique os campos.",
            errors=serializer.errors,
        )

    user = serializer.save()

    dados = {
        "cnpj": data.get("cnpj", ""),
        "endereco": data.get("endereco", ""),
        "especialidades": data.get("especialidade", ""),
        "telefone": data.get("telefone", ""),
        "motivacao": data.get("motivacao", ""),
    }

    doc = (
        request.FILES.get("contratoSocial")
        or request.FILES.get("alvaraFuncionamento")
        or request.FILES.get("crmClinica")
    )

    SolicitacaoCadastro.objects.create(
        solicitante=user,
        tipo=SolicitacaoCadastro.Tipo.CLINICA,
        dados_adicionais=dados,
        documento_comprobatorio=doc,
    )

    log_audit(request, LogAuditoria.Acao.CRIAR, modelo="CustomUser", pk_objeto=str(user.id))

    return api_created(
        data={"user_id": user.id, "email": user.email, "role": "paciente", "pendente_aprovacao": True},
        message="Conta criada! Você já pode acessar como Paciente enquanto sua solicitação de Clínica é analisada (2–5 dias úteis).",
    )


# ── Change Password ───────────────────────────────────────────────────────────
@extend_schema(tags=["Auth"], summary="Troca de senha")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """POST /api/auth/change-password/"""
    serializer = ChangePasswordSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        return api_error(message="Erro na troca de senha.", errors=serializer.errors)

    request.user.set_password(serializer.validated_data["new_password"])
    request.user.save()

    log_audit(request, LogAuditoria.Acao.ALTERAR_SENHA)

    return api_success(message="Senha alterada com sucesso. Faça login novamente.")


# ── Gov.br OAuth2 ─────────────────────────────────────────────────────────────
@extend_schema(
    tags=["Gov.br"],
    summary="Iniciar vinculação com Gov.br",
    description="Retorna a URL de autorização OAuth2 do Gov.br para vincular a conta do médico.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsDoctor])
def govbr_authorize_view(request):
    """
    GET /api/auth/govbr/authorize/
    Gera a URL de redirecionamento para o Gov.br.
    """
    state_token = govbr_service.gerar_state_token()

    # Salva o state na sessão para verificação no callback
    request.session["govbr_state"] = state_token
    request.session["govbr_user_id"] = str(request.user.id)
    request.session.modified = True

    redirect_url = govbr_service.gerar_url_autorizacao(state_token)

    return api_success(
        data={"redirect_url": redirect_url},
        message="Redirecione o usuário para a URL de autorização do Gov.br.",
    )


@extend_schema(
    tags=["Gov.br"],
    summary="Callback Gov.br — finaliza vinculação",
    description="Recebe o código de autorização do Gov.br e vincula a conta do médico.",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def govbr_callback_view(request):
    """
    GET /api/auth/govbr/callback/?code=...&state=...
    Callback OAuth2 do Gov.br.
    """
    code = request.GET.get("code")
    state = request.GET.get("state")

    if not code or not state:
        return api_error("Parâmetros inválidos no callback do Gov.br.")

    # Verificar anti-CSRF
    session_state = request.session.get("govbr_state")
    if not session_state or session_state != state:
        return api_error("Estado CSRF inválido. Reinicie o processo de vinculação.")

    user_id = request.session.get("govbr_user_id")

    try:
        # 1. Trocar código por tokens
        token_data = govbr_service.trocar_codigo_por_token(code)

        # 2. Obter informações do usuário (CPF/sub)
        userinfo = govbr_service.obter_informacoes_usuario(token_data["access_token"])

        # 3. Salvar dados Gov.br no perfil do médico
        user = CustomUser.objects.get(id=user_id)

        if not hasattr(user, "medico"):
            return api_error("Apenas médicos podem vincular conta ao Gov.br.")

        medico = user.medico
        medico.govbr_sub = userinfo.get("sub")
        medico.is_govbr_linked = True
        medico.save(update_fields=["govbr_sub", "is_govbr_linked"])

        # Limpar sessão
        del request.session["govbr_state"]
        del request.session["govbr_user_id"]

        log_audit(request, LogAuditoria.Acao.VINCULAR_GOVBR, modelo="Medico", pk_objeto=str(medico.id))

        return api_success(
            data={"linked": True, "govbr_sub": userinfo.get("sub")},
            message="Conta vinculada ao Gov.br com sucesso! Agora você pode assinar receitas digitalmente.",
        )

    except GovBrTimeoutError as e:
        return api_service_unavailable(str(e))

    except GovBrAuthError as e:
        return api_error(str(e), http_status=status.HTTP_401_UNAUTHORIZED)

    except CustomUser.DoesNotExist:
        return api_error("Sessão expirada. Reinicie o processo.", http_status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        logger.error(f"Gov.br callback error: {e}", exc_info=True)
        return api_error("Erro inesperado durante vinculação com Gov.br.")
