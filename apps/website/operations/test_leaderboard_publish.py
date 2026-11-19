import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from operations import leaderboard_publish as publisher
from operations.models import DailyLeaderboardJob as Job, DailyLeaderboardSchedule as Schedule


class DailyLeaderboardTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        executable = self.root / "steamcmd.exe"
        executable.touch()
        self.settings_override = override_settings(
            STAGING_ENVIRONMENT=True, LEADERBOARD_PUBLISH_ENABLED=True,
            LEADERBOARD_WORKSHOP_ID=publisher.TEST_ITEM_ID,
            LEADERBOARD_STEAM_USERNAME="TestOwner",
            LEADERBOARD_PACKAGE_ROOT=str(self.root / "packages"),
            STEAMCMD_EXECUTABLE=str(executable),
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.schedule = Schedule.objects.create(pk=1, enabled=True)

    def test_local_time_and_daily_deduplication(self):
        # London is UTC+1 in July.
        before = datetime(2026, 7, 2, 7, 59, tzinfo=timezone.utc)
        due = datetime(2026, 7, 2, 8, 0, tzinfo=timezone.utc)
        self.assertIsNone(publisher.enqueue(scheduled=True, now=before))
        job = publisher.enqueue(scheduled=True, now=due)
        job.status = Job.Status.UNCHANGED
        job.save()
        self.assertEqual(publisher.enqueue(scheduled=True, now=due).pk, job.pk)
        self.assertEqual(Job.objects.count(), 1)

    def test_disabled_schedule_does_not_enqueue(self):
        self.schedule.enabled = False
        self.schedule.save()
        self.assertIsNone(publisher.enqueue(scheduled=True))

    def test_missing_optional_day_is_nil(self):
        self.assertEqual(publisher.lua({"day": None}), '{["day"]=nil}')

    def test_production_and_other_item_refused(self):
        with override_settings(STAGING_ENVIRONMENT=False), self.assertRaises(ValueError):
            publisher.enqueue()
        with override_settings(LEADERBOARD_WORKSHOP_ID="3792308588"), self.assertRaises(ValueError):
            publisher.enqueue()
        self.assertFalse(Job.objects.exists())

    def test_package_keeps_unlisted_target_and_escapes_text(self):
        job = publisher.enqueue()
        target = publisher.package(job, [{"racer": 'x"\\\n123'}], self.root / "packages")
        vdf = (target / "upload.vdf").read_text()
        self.assertIn('"visibility" "3"', vdf)
        self.assertIn('"publishedfileid" "3842654789"', vdf)
        data = (target / "Contents/mods/TGSRRDailyLeaderboardProbe/42/media/lua/client/TGSRRDailyLeaderboardData.lua").read_text()
        self.assertIn('x\\"\\\\\\010123', data)

    @patch.object(publisher, "notify_superusers")
    @patch.object(publisher, "snapshot", return_value=[])
    @patch.object(publisher, "steam")
    def test_timeout_requires_review_and_blocks_later_upload(self, steam, snapshot, notify):
        steam.side_effect = subprocess.TimeoutExpired("steamcmd", 300)
        job = publisher.enqueue()
        publisher.publish(job)
        self.assertEqual(job.status, Job.Status.UNCERTAIN)
        self.assertEqual(publisher.enqueue().pk, job.pk)
        self.assertEqual(steam.call_count, 1)

    @patch.object(publisher, "snapshot", return_value=[])
    @patch.object(publisher, "steam")
    def test_unchanged_snapshot_skips_steam(self, steam, snapshot):
        Job.objects.create(schedule=self.schedule, status=Job.Status.PUBLISHED,
                           item_id=publisher.TEST_ITEM_ID, content_hash=publisher.data_hash([]))
        job = publisher.enqueue()
        publisher.publish(job)
        self.assertEqual(job.status, Job.Status.UNCHANGED)
        steam.assert_not_called()

    @patch.object(publisher, "notify_superusers")
    @patch.object(publisher, "snapshot", side_effect=ValueError("database unavailable"))
    @patch.object(publisher, "steam")
    def test_snapshot_failure_never_uploads_empty_replacement(self, steam, snapshot, notify):
        job = publisher.enqueue()
        publisher.publish(job)
        self.assertEqual(job.status, Job.Status.FAILED)
        steam.assert_not_called()
