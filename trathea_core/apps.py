"""
trathea_core/apps.py
AppConfig do trathea_core.
"""
from django.apps import AppConfig


class TratheaCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trathea_core"
    verbose_name = "Trathea Core — Biblioteca Central"
