"""WSGI config for Trathea project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trathea_orchestrator.settings.dev")
application = get_wsgi_application()
