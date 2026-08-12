from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from .models import RateLimitBucket, WorkerHeartbeatRecord
from .deployment_checks import production_deployment_checks
from .runtime_state import (
    clear_rate_limit,
    clear_worker_heartbeat_state,
    get_worker_heartbeat_state,
    increment_rate_limit,
    rate_limit_attempts,
    rate_limit_exceeded,
    record_worker_heartbeat_state,
    runtime_state_ready,
)


class ProductionDeploymentSettingsTests(TestCase):
    @override_settings(DEBUG=False)
    def test_windows_production_settings_are_accepted(self):
        with patch.dict(
            "os.environ",
            {"DJANGO_SETTINGS_MODULE": "config.settings_windows_production"},
        ):
            self.assertTrue(
                production_deployment_checks()["production settings"]
            )


@override_settings(RUNTIME_STATE_BACKEND="database")
class DatabaseRuntimeStateTests(TestCase):
    def test_rate_limit_counts_and_clears_attempts(self):
        self.assertFalse(rate_limit_exceeded("signup", "Player@Example.com", 2, 60))
        self.assertFalse(rate_limit_exceeded("signup", "player@example.com", 2, 60))
        self.assertTrue(rate_limit_exceeded("signup", "PLAYER@example.com", 2, 60))
        self.assertEqual(rate_limit_attempts("signup", "player@example.com"), 3)

        clear_rate_limit("signup", "player@example.com")

        self.assertEqual(rate_limit_attempts("signup", "player@example.com"), 0)

    def test_expired_rate_limit_starts_a_new_window(self):
        increment_rate_limit("password-reset", "example", 60)
        RateLimitBucket.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        self.assertEqual(increment_rate_limit("password-reset", "example", 60), 1)

    def test_worker_heartbeat_is_shared_and_release_aware(self):
        record_worker_heartbeat_state("worker-1", "release-123", 42)

        self.assertEqual(
            get_worker_heartbeat_state(),
            {
                "worker_id": "worker-1",
                "recorded_at": WorkerHeartbeatRecord.objects.get().recorded_at.isoformat(),
                "release_id": "release-123",
                "process_id": 42,
            },
        )

        clear_worker_heartbeat_state("another-worker")
        self.assertIsNotNone(get_worker_heartbeat_state())
        clear_worker_heartbeat_state("worker-1")
        self.assertIsNone(get_worker_heartbeat_state())

    def test_old_worker_heartbeat_is_not_ready(self):
        record_worker_heartbeat_state("worker-1", "release-123", 42)
        WorkerHeartbeatRecord.objects.update(
            recorded_at=timezone.now() - timedelta(minutes=5)
        )

        self.assertIsNone(get_worker_heartbeat_state())

    def test_runtime_state_readiness_uses_database(self):
        self.assertTrue(runtime_state_ready())


@skipUnless(connection.vendor == "postgresql", "PostgreSQL-specific concurrency test")
@override_settings(RUNTIME_STATE_BACKEND="database")
class PostgreSQLAtomicRateLimitTests(TransactionTestCase):
    reset_sequences = True

    @staticmethod
    def _increment():
        close_old_connections()
        try:
            return increment_rate_limit("concurrency", "same-client", 60)
        finally:
            connections.close_all()

    def test_concurrent_attempts_are_not_lost(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            attempts = list(executor.map(lambda _: self._increment(), range(16)))

        self.assertEqual(sorted(attempts), list(range(1, 17)))
        self.assertEqual(rate_limit_attempts("concurrency", "same-client"), 16)
