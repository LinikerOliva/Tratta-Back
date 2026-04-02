"""
core_app/serializers.py
Serializers de autenticação e usuário.
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from trathea_core.utils.validators import validate_cpf
from trathea_core.utils.sanitizers import sanitize_html

from core_app.models import CustomUser, UserProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT Token com claims extras (role, nome)."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["nome"] = user.nome_completo
        token["email"] = user.email
        return token


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ["user"]

    def validate_cpf(self, value):
        cpf_limpo = "".join(filter(str.isdigit, value))
        if not validate_cpf(cpf_limpo):
            raise serializers.ValidationError("CPF inválido.")
        return cpf_limpo


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer para exibição do usuário (sem senha)."""

    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id", "email", "nome_completo", "role",
            "is_active", "is_verified", "date_joined", "profile",
        ]
        read_only_fields = ["id", "date_joined", "is_verified"]


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer para cadastro de novos usuários."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    cpf = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ["email", "nome_completo", "role", "password", "password_confirm", "cpf"]

    def validate_email(self, value):
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este email já está cadastrado.")
        return value.lower()

    def validate_nome_completo(self, value):
        return sanitize_html(value)

    def validate_cpf(self, value):
        if not value:
            return value
        cpf_limpo = "".join(filter(str.isdigit, value))
        if not validate_cpf(cpf_limpo):
            raise serializers.ValidationError("CPF inválido.")
        if UserProfile.objects.filter(cpf=cpf_limpo).exists():
            raise serializers.ValidationError("CPF já cadastrado no sistema.")
        return cpf_limpo

    def validate_role(self, value):
        # Apenas admin pode criar outros admins
        request = self.context.get("request")
        if value == "admin" and (not request or not request.user.is_authenticated or not request.user.is_admin):
            raise serializers.ValidationError("Não é permitido criar usuário com perfil admin.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "As senhas não coincidem."})
        return attrs

    def create(self, validated_data):
        cpf = validated_data.pop("cpf", None)
        user = CustomUser.objects.create_user(**validated_data)
        # Cria o perfil com CPF (se fornecido) ou sem CPF (para casos de clínica/CNPJ)
        if cpf:
            UserProfile.objects.create(user=user, cpf=cpf)
        else:
            UserProfile.objects.create(user=user, cpf=None)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para troca de senha."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Senha atual incorreta.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "As senhas não coincidem."})
        return attrs
