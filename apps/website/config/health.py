import tempfile
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from operations.worker_health import HEARTBEAT_CACHE_KEY


def _database_ready():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)


def _cache_ready():
    key = "health:readiness"
    cache.set(key, "ready", timeout=10)
    ready = cache.get(key) == "ready"
    cache.delete(key)
    return ready


def _directory_writable(value):
    directory = Path(value)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, prefix=".health-", delete=True):
        return True


@never_cache
@require_GET
def liveness(request):
    return JsonResponse(
        {
            "status": "alive",
            "release": settings.RELEASE_ID,
        }
    )


@never_cache
@require_GET
def readiness(request):
    checks = {}
    operations = {
        "database": _database_ready,
        "cache": _cache_ready,
        "media_storage": lambda: _directory_writable(settings.MEDIA_ROOT),
        "private_storage": lambda: _directory_writable(
            settings.AVATAR_QUARANTINE_ROOT
        ),
        "reference_storage": lambda: _directory_writable(settings.PZ_REFERENCE_ROOT),
        "decompiled_storage": lambda: _directory_writable(
            settings.PZ_DECOMPILED_ROOT
        ),
    }
    for name, operation in operations.items():
        try:
            checks[name] = bool(operation())
        except Exception:
            checks[name] = False

    heartbeat = cache.get(HEARTBEAT_CACHE_KEY)
    checks["reference_worker"] = bool(
        heartbeat and heartbeat.get("release_id") == settings.RELEASE_ID
    )
    ready = all(checks.values())
    return JsonResponse(
        {
            "status": "ready" if ready else "unavailable",
            "release": settings.RELEASE_ID,
            "checks": checks,
        },
        status=200 if ready else 503,
    )
