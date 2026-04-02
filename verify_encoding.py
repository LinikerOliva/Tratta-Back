import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trathea_orchestrator.settings.dev")
django.setup()

from paciente_app.models import Paciente
from core_app.models import CustomUser

user = CustomUser.objects.filter(email='ana.beatriz@email.com').first()
paciente = Paciente.objects.filter(user=user).first()
print(f"Current allergy: {paciente.alergias}")
