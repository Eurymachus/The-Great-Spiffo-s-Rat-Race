from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import RateLimitBucket, WorkerHeartbeatRecord


class RuntimePruningTests(TestCase):
    def test_preview_preserves_everything_and_apply_preserves_live_state(self):
        RateLimitBucket.objects.create(key="expired", expires_at=timezone.now() - timedelta(seconds=1), attempts=3)
        RateLimitBucket.objects.create(key="active", expires_at=timezone.now() + timedelta(hours=1), attempts=5)
        heartbeat = WorkerHeartbeatRecord.objects.create(key="worker", worker_id="test", process_id=1, release_id="test", recorded_at=timezone.now())
        call_command("prune_runtime_state", stdout=StringIO())
        self.assertEqual(RateLimitBucket.objects.count(), 2)
        call_command("prune_runtime_state", apply=True, stdout=StringIO())
        self.assertEqual(list(RateLimitBucket.objects.values_list("key", "attempts")), [("active", 5)])
        self.assertTrue(WorkerHeartbeatRecord.objects.filter(pk=heartbeat.pk).exists())
