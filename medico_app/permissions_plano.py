"""
medico_app/permissions_plano.py
Permissões customizadas baseadas no plano de assinatura do médico.

Uso nas views:
    permission_classes = [IsAuthenticated, IsDoctor, HasTranscriptionQuota]

Essas permissões são "guard gates" — o frontend já bloqueia
a UI (via campos do serializer), mas o backend garante a regra.
"""
import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger("trathea")


class _BasePlanPermission(BasePermission):
    """Classe base com resolução do objeto AssinaturaMedico."""

    def _get_assinatura(self, request):
        """Resolve a assinatura do médico a partir do request.user."""
        user = request.user
        if not user or not user.is_authenticated:
            return None

        # Admin tem acesso irrestrito (para testes/suporte)
        if user.role == "admin":
            return None  # sinaliza bypass

        medico = getattr(user, "medico", None)
        if not medico:
            return False  # sem perfil médico = negar

        assinatura = getattr(medico, "assinatura", None)
        if not assinatura:
            return False  # sem assinatura = negar

        return assinatura


class HasTranscriptionQuota(_BasePlanPermission):
    """
    Verifica se o médico tem saldo de transcrições IA no ciclo atual.

    Aplicar nos endpoints:
    - estruturar_transcricao_ia_view
    - Qualquer endpoint que consuma IA/Gemini
    """

    message = (
        "Você atingiu o limite de transcrições do seu plano. "
        "Faça upgrade para continuar usando a IA."
    )

    def has_permission(self, request, view):
        assinatura = self._get_assinatura(request)
        if assinatura is None:
            return True  # admin bypass
        if assinatura is False:
            return False  # sem assinatura
        return assinatura.pode_transcrever()


class HasSignatureQuota(_BasePlanPermission):
    """
    Verifica se o médico tem saldo de assinaturas Gov.br no ciclo atual.

    Aplicar nos endpoints:
    - assinar_receita_govbr_view
    - finalizar_consulta_completa_view (quando tipo_assinatura='govbr')
    """

    message = (
        "Você atingiu o limite de assinaturas digitais do seu plano. "
        "Faça upgrade para continuar assinando documentos."
    )

    def has_permission(self, request, view):
        assinatura = self._get_assinatura(request)
        if assinatura is None:
            return True  # admin bypass
        if assinatura is False:
            return False
        return assinatura.pode_assinar_govbr()


class HasAdvancedDashboard(_BasePlanPermission):
    """
    Verifica se o plano do médico inclui o dashboard avançado.

    Aplicar nos endpoints de métricas de produtividade.
    """

    message = (
        "O dashboard avançado não está disponível no seu plano. "
        "Faça upgrade para o Professional ou superior."
    )

    def has_permission(self, request, view):
        assinatura = self._get_assinatura(request)
        if assinatura is None:
            return True  # admin bypass
        if assinatura is False:
            return False
        return assinatura.plano.tem_dashboard_avancado


class HasActivePlan(_BasePlanPermission):
    """
    Verifica se o médico tem uma assinatura ativa (qualquer plano).
    Útil como gate genérico antes de acessar funcionalidades premium.
    """

    message = (
        "Sua assinatura está inativa ou suspensa. "
        "Regularize seu plano para continuar usando o Tratta."
    )

    def has_permission(self, request, view):
        assinatura = self._get_assinatura(request)
        if assinatura is None:
            return True  # admin bypass
        if assinatura is False:
            return False
        return assinatura.is_ativa


class HasFeature(_BasePlanPermission):
    """
    Permissão genérica baseada em feature flag do plano.

    Uso:
        class MinhaView(APIView):
            permission_classes = [IsAuthenticated, HasFeature]
            plan_feature = "tem_multi_usuarios"  # atributo da view

    A view define qual feature flag verificar.
    """

    message = "Esta funcionalidade não está disponível no seu plano atual."

    def has_permission(self, request, view):
        assinatura = self._get_assinatura(request)
        if assinatura is None:
            return True
        if assinatura is False:
            return False

        feature_name = getattr(view, "plan_feature", None)
        if not feature_name:
            logger.warning(
                f"View {view.__class__.__name__} usa HasFeature "
                f"mas não definiu plan_feature."
            )
            return True  # fail open se mal configurado

        return getattr(assinatura.plano, feature_name, False)
