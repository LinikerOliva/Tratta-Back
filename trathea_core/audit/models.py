"""
trathea_core/audit/models.py
Modelo de Log de Auditoria — registra todas as operações críticas.
"""
from django.db import models
from django.conf import settings


class LogAuditoria(models.Model):
    """
    Registro imutável de auditoria.
    NUNCA deletar ou editar registros desta tabela.
    """

    # ── Tipos de Ação ─────────────────────────────────────────────────────────
    class Acao(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        ALTERAR_SENHA = "ALTERAR_SENHA", "Alteração de Senha"
        VINCULAR_GOVBR = "VINCULAR_GOVBR", "Vinculação Gov.br"
        CRIAR_RECEITA = "CRIAR_RECEITA", "Criação de Receita"
        EDITAR_RECEITA = "EDITAR_RECEITA", "Edição de Receita"
        DELETAR_RECEITA = "DELETAR_RECEITA", "Exclusão de Receita"
        ASSINAR_RECEITA = "ASSINAR_RECEITA", "Assinatura de Receita (Gov.br)"
        ENVIAR_RECEITA = "ENVIAR_RECEITA", "Envio de Receita ao Paciente"
        CRIAR_PRONTUARIO = "CRIAR_PRONTUARIO", "Criação de Prontuário"
        EDITAR_PRONTUARIO = "EDITAR_PRONTUARIO", "Edição de Prontuário"
        APROVAR_SOLICITACAO = "APROVAR_SOLICITACAO", "Aprovação de Solicitação"
        REJEITAR_SOLICITACAO = "REJEITAR_SOLICITACAO", "Rejeição de Solicitação"
        EXPORT_RELATORIO = "EXPORT_RELATORIO", "Exportação de Relatório"
        UPLOAD_CERTIFICADO = "UPLOAD_CERTIFICADO", "Upload de Certificado"
        DELETAR_CERTIFICADO = "DELETAR_CERTIFICADO", "Remoção de Certificado"
        ACESSO_NEGADO = "ACESSO_NEGADO", "Tentativa de Acesso Negada"
        # ── Configurações ──────────────────────────────────────────────────
        CRIAR = "CRIAR", "Criação de Registro"
        ATUALIZAR = "ATUALIZAR", "Atualização de Dados"
        DELETAR = "DELETAR", "Exclusão de Registro"
        ALTERAR_DADOS_CRITICOS = "ALTERAR_DADOS_CRITICOS", "Alteração de Dados Críticos (CRM/CNPJ)"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_auditoria",
        verbose_name="Usuário",
    )
    acao = models.CharField(
        max_length=50,
        choices=Acao.choices,
        verbose_name="Ação",
        db_index=True,
    )
    modelo = models.CharField(
        max_length=100,
        verbose_name="Modelo afetado",
        blank=True,
        db_index=True,
    )
    pk_objeto = models.CharField(
        max_length=100,
        verbose_name="ID do objeto afetado",
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="Endereço IP",
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        verbose_name="User Agent",
        blank=True,
    )
    dados_extra = models.JSONField(
        verbose_name="Dados adicionais",
        null=True,
        blank=True,
        help_text="Snapshot antes/depois da alteração ou dados relevantes.",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data/Hora",
        db_index=True,
    )

    class Meta:
        app_label = "trathea_core"
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["usuario", "acao"]),
            models.Index(fields=["modelo", "pk_objeto"]),
        ]

    def __str__(self):
        usuario_str = self.usuario.email if self.usuario else "Sistema"
        return f"[{self.timestamp:%d/%m/%Y %H:%M}] {usuario_str} — {self.acao}"
