import os
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from registry.models import StreamingAccount
from registry.streaming import decrypt_token

from .runtime_state import runtime_state_ready, uses_database_runtime_state


def executable_available(value):
    candidate = str(value).strip()
    if not candidate:
        return False
    path = Path(candidate)
    if path.is_absolute() or path.parent != Path("."):
        return path.is_file()
    return shutil.which(candidate) is not None


def directory_writable(value):
    directory = Path(value)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, prefix=".deploy-", delete=True):
        return True


def database_available():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)


def migrations_current():
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    return not executor.migration_plan(targets)


def stored_provider_tokens_decryptable():
    fields = ("encrypted_access_token", "encrypted_refresh_token")
    for account in StreamingAccount.objects.only(*fields).iterator():
        for field in fields:
            encrypted_token = getattr(account, field)
            if encrypted_token:
                decrypt_token(encrypted_token)
    return True


def production_deployment_checks():
    state_check_name = (
        "runtime state" if uses_database_runtime_state() else "cache"
    )
    return {
        "production settings": (
            os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings_production"
            and settings.DEBUG is False
        ),
        "database": database_available,
        state_check_name: runtime_state_ready,
        "migrations": migrations_current,
        "stored provider credentials": stored_provider_tokens_decryptable,
        "static storage": lambda: directory_writable(settings.STATIC_ROOT),
        "media storage": lambda: directory_writable(settings.MEDIA_ROOT),
        "private storage": lambda: directory_writable(
            settings.AVATAR_QUARANTINE_ROOT
        ),
        "reference storage": lambda: directory_writable(settings.PZ_REFERENCE_ROOT),
        "decompiled storage": lambda: directory_writable(
            settings.PZ_DECOMPILED_ROOT
        ),
        "SteamCMD": lambda: executable_available(settings.STEAMCMD_EXECUTABLE),
        "Java": lambda: executable_available(settings.JAVA_EXECUTABLE),
        "Vineflower": lambda: Path(settings.VINEFLOWER_JAR).is_file(),
    }


def evaluate_production_deployment_checks():
    results = {}
    for name, operation in production_deployment_checks().items():
        try:
            results[name] = bool(operation() if callable(operation) else operation)
        except Exception:
            results[name] = False
    return results
