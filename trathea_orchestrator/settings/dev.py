"""
TRATHEA — Settings de Desenvolvimento
DEBUG=True, SQLite, email no console.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# ── Email console ─────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── CORS permissivo em dev ────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Logging em dev ────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "trathea": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
