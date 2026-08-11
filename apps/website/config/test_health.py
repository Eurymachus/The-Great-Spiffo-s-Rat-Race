import tempfile
from pathlib import Path

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from operations.worker_health import HEARTBEAT_CACHE_KEY


class HealthEndpointTests(TestCase):
    def test_liveness_identifies_release_without_dependency_checks(self):
        with override_settings(RELEASE_ID="release-123"):
            response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive", "release": "release-123"})

    def test_readiness_checks_database_cache_storage_and_worker(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            with override_settings(
                RELEASE_ID="release-123",
                MEDIA_ROOT=root / "media",
                AVATAR_QUARANTINE_ROOT=root / "private",
                PZ_REFERENCE_ROOT=root / "reference",
                PZ_DECOMPILED_ROOT=root / "decompiled",
            ):
                cache.set(
                    HEARTBEAT_CACHE_KEY,
                    {"release_id": "release-123"},
                    timeout=60,
                )
                response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertTrue(all(response.json()["checks"].values()))

    def test_readiness_rejects_missing_or_old_worker(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            with override_settings(
                RELEASE_ID="current-release",
                MEDIA_ROOT=root / "media",
                AVATAR_QUARANTINE_ROOT=root / "private",
                PZ_REFERENCE_ROOT=root / "reference",
                PZ_DECOMPILED_ROOT=root / "decompiled",
            ):
                cache.set(
                    HEARTBEAT_CACHE_KEY,
                    {"release_id": "previous-release"},
                    timeout=60,
                )
                response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["checks"]["reference_worker"])
