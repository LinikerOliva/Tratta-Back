from django.apps import AppConfig


class MedicoAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "medico_app"
    verbose_name = "Médico"

    def ready(self):
        # Registra signals de auto-provisionamento de plano Starter
        import medico_app.signals_plano  # noqa: F401
