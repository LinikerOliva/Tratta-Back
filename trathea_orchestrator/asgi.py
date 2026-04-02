"""ASGI config for Trathea project — pronto para WebSocket/async."""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trathea_orchestrator.settings.dev")
application = get_asgi_application()
