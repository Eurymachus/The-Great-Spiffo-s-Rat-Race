import hashlib
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.utils import timezone

from .models import RateLimitBucket, WorkerHeartbeatRecord


REFERENCE_WORKER_HEARTBEAT_KEY = "reference-worker"


def uses_database_runtime_state():
    return getattr(settings, "RUNTIME_STATE_BACKEND", "cache") == "database"


def _bucket_key(scope, identifier):
    digest = hashlib.sha256(identifier.casefold().encode("utf-8")).hexdigest()
    return f"{scope}:{digest}"[:96]


def _database_increment(key, window_seconds):
    now = timezone.now()
    expires_at = now + timedelta(seconds=window_seconds)
    if connection.vendor == "postgresql":
        table = connection.ops.quote_name(RateLimitBucket._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {table} (key, attempts, expires_at)
                VALUES (%s, 1, %s)
                ON CONFLICT (key) DO UPDATE SET
                    attempts = CASE
                        WHEN {table}.expires_at <= %s THEN 1
                        ELSE {table}.attempts + 1
                    END,
                    expires_at = CASE
                        WHEN {table}.expires_at <= %s THEN EXCLUDED.expires_at
                        ELSE {table}.expires_at
                    END
                RETURNING attempts
                """,
                [key, expires_at, now, now],
            )
            return cursor.fetchone()[0]

    with transaction.atomic():
        bucket = RateLimitBucket.objects.select_for_update().filter(pk=key).first()
        if bucket is None:
            RateLimitBucket.objects.create(
                key=key, attempts=1, expires_at=expires_at
            )
            return 1
        if bucket.expires_at <= now:
            bucket.attempts = 1
            bucket.expires_at = expires_at
        else:
            bucket.attempts += 1
        bucket.save(update_fields=("attempts", "expires_at"))
        return bucket.attempts


def rate_limit_exceeded(scope, identifier, limit, window_seconds):
    key = _bucket_key(scope, identifier)
    if uses_database_runtime_state():
        return _database_increment(key, window_seconds) > limit
    cache_key = f"rat-race-rate:{key}"
    if cache.add(cache_key, 1, timeout=window_seconds):
        return False
    try:
        attempts = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        return False
    return attempts > limit


def rate_limit_attempts(scope, identifier):
    key = _bucket_key(scope, identifier)
    if uses_database_runtime_state():
        bucket = RateLimitBucket.objects.filter(
            pk=key, expires_at__gt=timezone.now()
        ).first()
        return bucket.attempts if bucket else 0
    return cache.get(f"rat-race-rate:{key}", 0)


def increment_rate_limit(scope, identifier, window_seconds):
    key = _bucket_key(scope, identifier)
    if uses_database_runtime_state():
        return _database_increment(key, window_seconds)
    cache_key = f"rat-race-rate:{key}"
    if cache.add(cache_key, 1, timeout=window_seconds):
        return 1
    try:
        return cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        return 1


def clear_rate_limit(scope, identifier):
    key = _bucket_key(scope, identifier)
    if uses_database_runtime_state():
        RateLimitBucket.objects.filter(pk=key).delete()
    else:
        cache.delete(f"rat-race-rate:{key}")


def record_worker_heartbeat_state(worker_id, release_id, process_id):
    if uses_database_runtime_state():
        WorkerHeartbeatRecord.objects.update_or_create(
            key=REFERENCE_WORKER_HEARTBEAT_KEY,
            defaults={
                "worker_id": worker_id,
                "release_id": release_id,
                "process_id": process_id,
                "recorded_at": timezone.now(),
            },
        )
        return
    cache.set(
        "operations:reference-worker:heartbeat",
        {
            "worker_id": worker_id,
            "recorded_at": timezone.now().isoformat(),
            "release_id": release_id,
            "process_id": process_id,
        },
        timeout=settings.REFERENCE_WORKER_HEARTBEAT_TTL_SECONDS,
    )


def get_worker_heartbeat_state():
    if uses_database_runtime_state():
        heartbeat = WorkerHeartbeatRecord.objects.filter(
            pk=REFERENCE_WORKER_HEARTBEAT_KEY,
            recorded_at__gte=timezone.now()
            - timedelta(seconds=settings.REFERENCE_WORKER_HEARTBEAT_TTL_SECONDS),
        ).first()
        if not heartbeat:
            return None
        return {
            "worker_id": heartbeat.worker_id,
            "recorded_at": heartbeat.recorded_at.isoformat(),
            "release_id": heartbeat.release_id,
            "process_id": heartbeat.process_id,
        }
    return cache.get("operations:reference-worker:heartbeat")


def clear_worker_heartbeat_state(worker_id):
    if uses_database_runtime_state():
        WorkerHeartbeatRecord.objects.filter(
            pk=REFERENCE_WORKER_HEARTBEAT_KEY, worker_id=worker_id
        ).delete()
        return
    current = cache.get("operations:reference-worker:heartbeat")
    if current and current.get("worker_id") == worker_id:
        cache.delete("operations:reference-worker:heartbeat")


def runtime_state_ready():
    if uses_database_runtime_state():
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    key = "operations:runtime-state-check"
    cache.set(key, "ready", timeout=10)
    ready = cache.get(key) == "ready"
    cache.delete(key)
    return ready
