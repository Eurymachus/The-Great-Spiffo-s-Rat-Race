import os
from pathlib import Path

from .production_environment import validate_production_environment
from .settings import *  # noqa: F403


production = validate_production_environment(os.environ)

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = production["allowed_hosts"]
CSRF_TRUSTED_ORIGINS = production["csrf_trusted_origins"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": production["postgres_port"],
        "CONN_MAX_AGE": production["postgres_conn_max_age"],
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "sslmode": os.environ.get("POSTGRES_SSLMODE", "require"),
        },
    }
}

RUNTIME_STATE_BACKEND = production["runtime_state_backend"]
if RUNTIME_STATE_BACKEND == "cache":
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ["REDIS_URL"],
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "rat-race-production-non-shared",
            "TIMEOUT": 300,
        }
    }

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

EMAIL_BACKEND = "config.graph_email.MicrosoftGraphEmailBackend"
MICROSOFT_GRAPH_TENANT_ID = os.environ["MICROSOFT_GRAPH_TENANT_ID"]
MICROSOFT_GRAPH_CLIENT_ID = os.environ["MICROSOFT_GRAPH_CLIENT_ID"]
MICROSOFT_GRAPH_CLIENT_SECRET = os.environ["MICROSOFT_GRAPH_CLIENT_SECRET"]
MICROSOFT_GRAPH_SENDER = os.environ["MICROSOFT_GRAPH_SENDER"]
DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", DEFAULT_FROM_EMAIL)

STATIC_ROOT = Path(os.environ["STATIC_ROOT"])
MEDIA_ROOT = Path(os.environ["MEDIA_ROOT"])
AVATAR_QUARANTINE_ROOT = Path(os.environ["AVATAR_QUARANTINE_ROOT"])

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = production["secure_hsts_seconds"]
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
TRUST_CLOUDFLARE_CONNECTING_IP = production["trust_cloudflare_connecting_ip"]

RELEASE_ID = os.environ["RELEASE_ID"]

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
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
