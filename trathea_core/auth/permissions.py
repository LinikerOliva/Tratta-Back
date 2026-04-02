"""
trathea_core/auth/permissions.py
Permissões RBAC reutilizáveis para toda a API Trathea.

Uso nas views:
    permission_classes = [IsAuthenticated, IsDoctor]
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsDoctor(BasePermission):
    """Permite acesso apenas a usuários com role='medico'."""

    message = "Acesso exclusivo para médicos."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "medico"
        )


class IsPatient(BasePermission):
    """Permite acesso apenas a usuários com role='paciente'."""

    message = "Acesso exclusivo para pacientes."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "paciente"
        )


class IsClinic(BasePermission):
    """Permite acesso apenas a usuários com role='clinica'."""

    message = "Acesso exclusivo para clínicas."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "clinica"
        )


class IsSecretary(BasePermission):
    """Permite acesso apenas a usuários com role='secretaria'."""

    message = "Acesso exclusivo para secretarias."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "secretaria"
        )


class IsAdminUser(BasePermission):
    """Permite acesso apenas a usuários com role='admin'."""

    message = "Acesso exclusivo para administradores."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsOwner(BasePermission):
    """
    Permite acesso apenas ao dono do objeto.
    O objeto deve ter um campo 'user' (FK para CustomUser).
    """

    message = "Você só pode acessar seus próprios recursos."

    def has_object_permission(self, request, view, obj):
        return bool(request.user and hasattr(obj, "user") and obj.user == request.user)


class IsDoctorOrReadOnly(BasePermission):
    """
    Médicos têm acesso de escrita; outros usuários autenticados têm leitura.
    """

    message = "Apenas médicos podem realizar esta operação de escrita."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "medico"
        )


class IsDoctorOrAdmin(BasePermission):
    """Permite acesso somente a médicos ou admins."""

    message = "Acesso restrito a médicos e administradores."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("medico", "admin")
        )


class IsMedicalStaff(BasePermission):
    """Permite acesso a médicos, secretarias e clínicas."""

    message = "Acesso restrito à equipe médica."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("medico", "secretaria", "clinica", "admin")
        )


class IsGovBrLinked(BasePermission):
    """
    Garante que o médico vinculou sua conta ao Gov.br.
    Necessário para operações de assinatura digital.
    """

    message = "É necessário vincular sua conta ao Gov.br para assinar documentos."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.role != "medico":
            return False
        try:
            return request.user.medico.is_govbr_linked
        except AttributeError:
            return False


class CanAccessPatientData(BasePermission):
    """
    Médicos e secretarias podem acessar dados de qualquer paciente.
    Pacientes só acessam os seus próprios dados.
    """

    message = "Você não tem permissão para acessar estes dados de paciente."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in ("medico", "secretaria", "clinica", "admin"):
            return True
        if user.role == "paciente":
            return hasattr(obj, "user") and obj.user == user
        return False
