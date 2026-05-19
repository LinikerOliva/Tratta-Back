"""
medico_app/signals_plano.py
Signals para criação automática de assinatura Starter ao criar um Medico.

Ao criar um novo perfil Médico, uma AssinaturaMedico com plano Starter
é automaticamente provisionada. Se o plano Starter não existir no banco,
ele é criado com os valores padrão do MVP.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from dateutil.relativedelta import relativedelta

logger = logging.getLogger("trathea")


@receiver(post_save, sender="medico_app.Medico")
def criar_assinatura_starter(sender, instance, created, **kwargs):
    """
    Cria automaticamente uma AssinaturaMedico com plano Starter
    quando um novo Medico é cadastrado.
    """
    if not created:
        return

    from .models_plano import Plano, AssinaturaMedico

    # Evitar duplicata (segurança)
    if hasattr(instance, "assinatura"):
        return

    # Buscar ou criar plano Starter
    plano_starter, plano_criado = Plano.objects.get_or_create(
        tipo=Plano.Tipo.STARTER,
        defaults={
            "nome": "Starter",
            "descricao": (
                "Ideal para médicos autônomos. Inclui agenda, prontuário, "
                "20 transcrições IA/mês e 30 assinaturas Gov.br/mês."
            ),
            "preco_mensal": 0,
            "limite_transcricoes": 20,
            "limite_assinaturas": 30,
            "tem_dashboard_avancado": False,
            "tem_suporte_prioritario": False,
            "tem_multi_usuarios": False,
            "tem_relatorios_faturamento": False,
        },
    )

    if plano_criado:
        logger.info("Plano Starter criado automaticamente via signal.")

    hoje = timezone.now().date()
    AssinaturaMedico.objects.create(
        medico=instance,
        plano=plano_starter,
        status=AssinaturaMedico.Status.ATIVA,
        transcricoes_usadas=0,
        assinaturas_usadas=0,
        ciclo_inicio=hoje,
        ciclo_fim=hoje + relativedelta(months=1),
    )

    logger.info(
        f"AssinaturaMedico Starter criada para {instance} "
        f"(ciclo: {hoje} → {hoje + relativedelta(months=1)})"
    )
