"""
medico_app/management/commands/resetar_ciclo_planos.py

Comando Django para resetar o ciclo mensal de consumo dos médicos.

Uso manual:
    python manage.py resetar_ciclo_planos

Automatização com cron / Celery Beat:
    # crontab (Linux): executar todo dia 1 às 00:05
    5 0 1 * * cd /app && python manage.py resetar_ciclo_planos

    # Celery Beat (settings.py):
    CELERY_BEAT_SCHEDULE = {
        'resetar-ciclo-planos': {
            'task': 'medico_app.tasks.resetar_ciclo_planos_task',
            'schedule': crontab(hour=0, minute=5, day_of_month=1),
        },
    }

O comando verifica quais assinaturas ativas têm ciclo_fim <= hoje
e reseta os contadores de transcrições e assinaturas usadas.
"""
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger("trathea")


class Command(BaseCommand):
    help = (
        "Reseta o ciclo mensal de consumo (transcrições e assinaturas) "
        "para todas as assinaturas ativas cujo ciclo expirou."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria resetado sem efetivamente alterar.",
        )
        parser.add_argument(
            "--force-all",
            action="store_true",
            help="Força o reset de TODAS as assinaturas ativas, independente do ciclo.",
        )

    def handle(self, *args, **options):
        from medico_app.models_plano import AssinaturaMedico

        dry_run = options["dry_run"]
        force_all = options["force_all"]
        hoje = timezone.now().date()

        # Buscar assinaturas ativas cujo ciclo expirou
        qs = AssinaturaMedico.objects.filter(
            status__in=[
                AssinaturaMedico.Status.ATIVA,
                AssinaturaMedico.Status.TRIAL,
            ]
        ).select_related("medico__user", "plano")

        if not force_all:
            qs = qs.filter(ciclo_fim__lte=hoje)

        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "Nenhuma assinatura precisa de reset no momento."
            ))
            return

        self.stdout.write(f"Encontradas {total} assinatura(s) para reset.")

        resetados = 0
        for assinatura in qs:
            medico_nome = assinatura.medico.user.nome_completo
            plano_nome = assinatura.plano.nome

            if dry_run:
                self.stdout.write(
                    f"  [DRY-RUN] {medico_nome} - {plano_nome} "
                    f"(IA: {assinatura.transcricoes_usadas}, "
                    f"Gov.br: {assinatura.assinaturas_usadas})"
                )
            else:
                old_ia = assinatura.transcricoes_usadas
                old_gov = assinatura.assinaturas_usadas
                assinatura.resetar_ciclo()
                resetados += 1
                self.stdout.write(
                    f"  [OK] {medico_nome} - {plano_nome} "
                    f"(IA: {old_ia}->0, Gov.br: {old_gov}->0, "
                    f"Novo ciclo: {assinatura.ciclo_inicio} -> {assinatura.ciclo_fim})"
                )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n[DRY-RUN] {total} assinatura(s) seriam resetadas."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n{resetados} assinatura(s) resetadas com sucesso."
            ))
            logger.info(f"Ciclo de planos resetado: {resetados} assinaturas.")
