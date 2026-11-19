import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from operations import leaderboard_publish as publisher
from operations.models import DailyLeaderboardJob as Job, DailyLeaderboardSchedule as Schedule
from registry.models import ChallengeMode


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

    @patch.object(publisher, "build_ranking_table")
    def test_snapshot_ranks_same_racer_separately_for_each_mode(self, rank):
        official = ChallengeMode.objects.create(key="official", display_name="Official", display_order=1)
        cdda = ChallengeMode.objects.create(key="cdda", display_name="CDDA", display_order=2)
        row = {
            "rank": 1, "racer": "Racer", "survivor": "Survivor", "completion": 10,
            "kills": 25, "outposts_completed": 0, "maxed_skills": 0, "in_game_day": 2,
        }
        rankings = {official.pk: [row], cdda.pk: [{**row, "kills": 12}]}
        rank.side_effect = lambda config: rankings.get(config["challenge_modes"][0], [])

        rows = publisher.snapshot()

        self.assertCountEqual(
            [call.args[0]["challenge_modes"] for call in rank.call_args_list],
            [[mode_id] for mode_id in ChallengeMode.objects.values_list("pk", flat=True)],
        )
        self.assertEqual(
            [(row["modeKey"], row["modeName"], row["racer"], row["rank"], row["kills"]) for row in rows],
            [("official", "Official", "Racer", 1, 25), ("cdda", "CDDA", "Racer", 1, 12)],
        )

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


    @patch.object(publisher, "snapshot", return_value=[])
    @patch.object(publisher, "steam")
    def test_run_now_uploads_unchanged_snapshot_and_verifies_download(self, steam, snapshot):
        Job.objects.create(
            schedule=self.schedule, status=Job.Status.PUBLISHED,
            item_id=publisher.TEST_ITEM_ID, content_hash=publisher.data_hash([]),
        )
        admin = get_user_model().objects.create_superuser(
            email="publisher@example.com", nickname="Publisher", password="test-password-only",
        )
        self.client.force_login(admin)
        run_now = reverse("admin:operations_dailyleaderboardschedule_run_now", args=[self.schedule.pk])
        schedule_page = reverse("admin:operations_dailyleaderboardschedule_change", args=[self.schedule.pk])
        self.assertRedirects(
            self.client.get(reverse("admin:operations_dailyleaderboardschedule_changelist")),
            schedule_page,
        )
        page = self.client.get(schedule_page)
        self.assertContains(page, "Run now")
        self.assertContains(page, 'type="time"')
        self.assertContains(page, 'value="09:00"')
        for field in ("name", "hour", "minute"):
            self.assertNotContains(page, f'name="{field}"')
        response = self.client.post(schedule_page, {
            "enabled": "on", "run_time": "14:25", "timezone_name": "Europe/London", "_save": "Save",
        }, follow=True)
        self.assertEqual(response.request["PATH_INFO"], schedule_page)
        self.schedule.refresh_from_db()
        self.assertEqual((self.schedule.hour, self.schedule.minute), (14, 25))
        self.assertEqual(self.client.get(run_now).status_code, 405)
        self.assertRedirects(self.client.post(run_now), schedule_page)
        job = Job.objects.get(status=Job.Status.QUEUED, force_upload=True)
        self.assertIsNone(job.scheduled_day)
        checkout = self.root / "steamapps/workshop/content/108600" / publisher.TEST_ITEM_ID

        def run_steam(executable, username, arguments):
            if arguments[0] == "+workshop_build_item":
                self.assertEqual(Path(arguments[1]).name, "upload.vdf")
                return subprocess.CompletedProcess([], 0, b"Committing update...Success", b"")
            self.assertEqual(arguments, ["+workshop_download_item", "108600", publisher.TEST_ITEM_ID, "validate"])
            shutil.copytree(self.root / "packages" / f"job-{job.pk}" / "Contents", checkout)
            return subprocess.CompletedProcess([], 0, b"Success. Downloaded item", b"")

        steam.side_effect = run_steam
        publisher.tick()
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PUBLISHED)
        self.assertEqual(steam.call_count, 2)

    @patch.object(publisher, "snapshot", return_value=[])
    @patch.object(publisher, "notify_superusers")
    @patch.object(publisher, "steam")
    def test_mismatch_blocks_publication_until_verified_reconciliation(self, steam, notify, snapshot):
        steam.side_effect = [
            subprocess.CompletedProcess([], 0, b"Committing update...Success", b""),
            subprocess.CompletedProcess([], 0, b"Success. Downloaded item", b""),
            subprocess.CompletedProcess([], 0, b"Success. Downloaded item", b""),
        ]
        job = publisher.enqueue()
        publisher.tick()
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.UNCERTAIN)
        checkout = self.root / "steamapps/workshop/content/108600" / publisher.TEST_ITEM_ID
        shutil.copytree(Path(job.package_path) / "Contents", checkout)
        self.assertEqual(publisher.reconcile(job.pk).status, Job.Status.PUBLISHED)

    @patch.object(publisher, "steam")
    def test_busy_steam_installation_leaves_job_queued(self, steam):
        job = publisher.enqueue()
        with publisher.steam_lock(self.root / "steamcmd.exe"):
            publisher.tick()
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.QUEUED)
        steam.assert_not_called()
