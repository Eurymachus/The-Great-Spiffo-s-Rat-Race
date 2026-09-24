import subprocess
import sys
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from datetime import timedelta

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from registry.models import Participant
from .job_output import LOG_LIMIT, run_logged_process, steam_console_progress
from .models import ReferenceSource, ReferenceUpdateJob


class LiveJobTests(TestCase):
    def test_branch_form_rejects_unknown_branch_and_uses_local_default(self):
        user = Participant.objects.create_superuser(
            email="branch@example.com", nickname="BranchAdmin", password="test-password",
        )
        self.client.force_login(user)
        url = reverse("admin:operations_referencesource_check_updates", args=[self.job.source_id])
        with self.settings(STEAMCMD_BRANCH="unstable"):
            page = self.client.get(url)
            self.assertContains(page, 'value="unstable" selected')
        before = ReferenceUpdateJob.objects.count()
        self.client.post(url, {"steam_branch": "invalid"})
        self.assertEqual(ReferenceUpdateJob.objects.count(), before)

    def test_queued_branch_survives_default_change(self):
        from .queue import enqueue_reference_update
        self.job.status = "updated"
        self.job.save()
        job, created = enqueue_reference_update(self.job.source, steam_branch="unstable")
        self.assertTrue(created)
        with self.settings(STEAMCMD_BRANCH="public"):
            job.refresh_from_db()
            self.assertEqual(job.steam_branch, "unstable")
            active, created = enqueue_reference_update(self.job.source, steam_branch="public")
            self.assertFalse(created)
            self.assertEqual(active.pk, job.pk)
            self.assertEqual(active.steam_branch, "unstable")

    def test_console_progress_excludes_old_jobs_and_login_output(self):
        now = timezone.now()
        stamp = now.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(hours=1)).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        with TemporaryDirectory() as directory:
            logs = Path(directory) / "logs"
            logs.mkdir()
            (logs / "console_log.txt").write_text(
                f"[{old}] Update state (0x5) verifying install, progress: 99.00\n"
                f"[{stamp}] Logging in user secret-account\n"
                f"[{stamp}] Update state (0x61) downloading, progress: 12.38\n",
                encoding="utf-8",
            )
            result = steam_console_progress(Path(directory) / "steamcmd.exe", now - timedelta(seconds=2))
            self.assertIn("12.38", result)
            self.assertNotIn("99.00", result)
            self.assertNotIn("secret-account", result)

    def setUp(self):
        self.job = ReferenceUpdateJob.objects.create(
            source=ReferenceSource.objects.get(), status="running",
            started_at=timezone.now(),
        )
        self.url = reverse("admin:operations_referenceupdatejob_live", args=[self.job.pk])

    def test_live_endpoint_requires_job_view_permission(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        user = Participant.objects.create_user(
            email="staff@example.com", nickname="Staff", password="test-password",
        )
        user.is_staff = True
        user.save()
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        user.user_permissions.add(Permission.objects.get(
            codename="view_referenceupdatejob", content_type__app_label="operations",
        ))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["active"])
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.job.status = "failed"
        self.job.finished_at = timezone.now()
        self.job.summary = "Tool failed."
        self.job.save()
        response = self.client.get(self.url)
        self.assertFalse(response.json()["active"])
        self.assertEqual(response.json()["summary"], "Tool failed.")
        page = self.client.get(reverse("admin:operations_referenceupdatejob_change", args=[self.job.pk]))
        self.assertContains(page, 'id="job-log"')
        self.assertContains(page, self.url)

    def test_output_is_visible_before_exit_and_redacted(self):
        # The fake child emits one chunk then remains running for one poll.
        with patch("operations.job_output.subprocess.Popen") as popen:
            process = popen.return_value.__enter__.return_value
            process.poll.side_effect = [None, 0]
            def start(*args, **kwargs):
                kwargs["stdout"].write(b"account-name\rUpdate state (0x61) downloading, progress: 42.50")
                kwargs["stdout"].flush()
                return popen.return_value
            popen.side_effect = start
            def check_while_running(_):
                self.job.refresh_from_db()
                self.assertIn("[account]", self.job.log_output)
                self.assertNotIn("account-name", self.job.log_output)
                self.assertEqual(self.job.progress_percent, 42.5)
            with patch("operations.job_output.time.sleep", side_effect=check_while_running):
                result = run_logged_process(["tool"], job=self.job, timeout=10,
                                            label="Starting", redact=("account-name",))
            self.assertEqual(result.returncode, 0)

    def test_real_process_captures_both_streams_and_bounds_tail(self):
        result = run_logged_process(
            [sys.executable, "-c", "import sys; print('x'*70000, flush=True); print('error detail', file=sys.stderr)"],
            job=self.job, timeout=10, label="Starting",
        )
        self.job.refresh_from_db()
        self.assertEqual(result.returncode, 0)
        self.assertLessEqual(len(self.job.log_output), LOG_LIMIT)
        self.assertIn("error detail", self.job.log_output)
        self.assertIsNone(self.job.progress_percent)

    def test_timeout_terminates_child(self):
        with patch("operations.job_output.subprocess.Popen") as popen:
            process = popen.return_value.__enter__.return_value
            process.poll.return_value = None
            with self.assertRaises(subprocess.TimeoutExpired):
                run_logged_process(["tool"], job=self.job, timeout=0, label="Starting")
            process.kill.assert_called_once()
            process.wait.assert_called_once()
