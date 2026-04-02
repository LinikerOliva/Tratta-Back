"""
core_app/models.py
Modelos de autenticação e usuário do sistema Trathea.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """Manager para o CustomUser com login por email."""

    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("O campo de email é obrigatório.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", CustomUser.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Usuário customizado do Trathea.
    Login por email. Role determina o perfil de acesso (RBAC).
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        MEDICO = "medico", "Médico"
        PACIENTE = "paciente", "Paciente"
        SECRETARIA = "secretaria", "Secretaria"
        CLINICA = "clinica", "Clínica"

    email = models.EmailField(unique=True, verbose_name="Email")
    nome_completo = models.CharField(max_length=200, verbose_name="Nome completo")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        verbose_name="Perfil de acesso",
        db_index=True,
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email verificado",
        help_text="True quando o email foi confirmado.",
    )
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="Data de cadastro")
    last_login = models.DateTimeField(null=True, blank=True, verbose_name="Último acesso")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo", "role"]

    class Meta:
        app_label = "core_app"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.nome_completo} <{self.email}> [{self.role}]"

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_medico(self) -> bool:
        return self.role == self.Role.MEDICO

    @property
    def is_paciente(self) -> bool:
        return self.role == self.Role.PACIENTE


class UserProfile(models.Model):
    """Perfil estendido do usuário — dados pessoais."""

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )
    foto = models.ImageField(upload_to="profiles/", null=True, blank=True)
    cpf = models.CharField(
        max_length=14,
        unique=True,
        null=True,
        blank=True,
        verbose_name="CPF",
        help_text="Formato: 000.000.000-00",
    )
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    data_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de nascimento")
    genero = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("masculino", "Masculino"),
            ("feminino", "Feminino"),
            ("outro", "Outro"),
            ("nao_informar", "Prefiro não informar"),
        ],
    )
    is_2fa_enabled = models.BooleanField(
        default=False,
        verbose_name="Autenticação em Duas Etapas (2FA)",
        help_text="Ativa a camada extra de segurança no login."
    )
    endereco_logradouro = models.CharField(max_length=200, blank=True)
    endereco_numero = models.CharField(max_length=20, blank=True)
    endereco_complemento = models.CharField(max_length=100, blank=True)
    endereco_bairro = models.CharField(max_length=100, blank=True)
    endereco_cidade = models.CharField(max_length=100, blank=True)
    endereco_estado = models.CharField(max_length=2, blank=True)
    endereco_cep = models.CharField(max_length=10, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core_app"
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self):
        return f"Perfil de {self.user.nome_completo}"
