"""
medico_app/management/commands/seed_planos.py

Popula o banco com os 3 planos padrão do Tratta (Starter, Professional, Enterprise).

Uso:
    python manage.py seed_planos
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria os planos padrão (Starter, Professional, Enterprise) se não existirem."

    def handle(self, *args, **options):
        from medico_app.models_plano import Plano

        planos = [
            {
                "tipo": Plano.Tipo.STARTER,
                "defaults": {
                    "nome": "Starter",
                    "descricao": (
                        "Ideal para médicos autônomos ou em início de carreira. "
                        "Inclui agenda completa, prontuário, 20 transcrições IA/mês "
                        "e 30 assinaturas Gov.br/mês. Suporte via e-mail."
                    ),
                    "preco_mensal": 0,
                    "limite_transcricoes": 20,
                    "limite_assinaturas": 30,
                    "tem_dashboard_avancado": False,
                    "tem_suporte_prioritario": False,
                    "tem_multi_usuarios": False,
                    "tem_relatorios_faturamento": False,
                },
            },
            {
                "tipo": Plano.Tipo.PROFESSIONAL,
                "defaults": {
                    "nome": "Professional",
                    "descricao": (
                        "Para clínicas com alto volume de pacientes. "
                        "Transcrições IA e assinaturas Gov.br ilimitadas, "
                        "dashboard avançado de produtividade e suporte prioritário."
                    ),
                    "preco_mensal": 149.90,
                    "limite_transcricoes": 0,  # ilimitado
                    "limite_assinaturas": 0,   # ilimitado
                    "tem_dashboard_avancado": True,
                    "tem_suporte_prioritario": True,
                    "tem_multi_usuarios": False,
                    "tem_relatorios_faturamento": False,
                },
            },
            {
                "tipo": Plano.Tipo.ENTERPRISE,
                "defaults": {
                    "nome": "Enterprise",
                    "descricao": (
                        "Para hospitais e policlínicas. Tudo do Professional, "
                        "multi-usuários, relatórios de faturamento e "
                        "integração com convênios. Preço sob consulta."
                    ),
                    "preco_mensal": 499.90,
                    "limite_transcricoes": 0,
                    "limite_assinaturas": 0,
                    "tem_dashboard_avancado": True,
                    "tem_suporte_prioritario": True,
                    "tem_multi_usuarios": True,
                    "tem_relatorios_faturamento": True,
                },
            },
        ]

        for plano_data in planos:
            obj, created = Plano.objects.get_or_create(
                tipo=plano_data["tipo"],
                defaults=plano_data["defaults"],
            )
            status = "CRIADO" if created else "ja existe"
            self.stdout.write(f"  {obj.nome}: {status}")

        self.stdout.write(self.style.SUCCESS("\nSeed de planos concluido."))
