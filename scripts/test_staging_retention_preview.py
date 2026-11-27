import subprocess
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import staging_retention_preview as preview


class StagingRetentionPreviewTests(unittest.TestCase):
    def test_runner_never_exposes_apply_option_and_child_uses_read_only(self):
        with patch("sys.argv", ["runner", "1234567", "--apply"]), redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as error:
                preview.main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn("SET TRANSACTION READ ONLY", preview.CHILD)
        self.assertIn("apply=False", preview.CHILD)

    def test_protected_target_and_inherited_connection_override(self):
        expected = {
            "DJANGO_SETTINGS_MODULE": "config.settings_windows_staging",
            "POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "ratrace", "POSTGRES_USER": "ratrace", "RELEASE_ID": "1234567",
            "PGOPTIONS": "wrong", "PGSERVICE": "wrong",
        }
        with patch.object(preview, "read_environment", return_value=expected):
            env = preview.staging_environment(Path("fixture"), "1234567")
            self.assertEqual(env["PGOPTIONS"], "-c default_transaction_read_only=on")
            self.assertNotIn("PGSERVICE", env)
            expected["POSTGRES_PORT"] = "5432"
            with self.assertRaises(ValueError):
                preview.staging_environment(Path("fixture"), "1234567")

    def test_unsafe_output_is_withheld_and_blocked_counts_require_review(self):
        blocked = "Candidates: 2; eligible: 0; blocked: 2; deleted: 0.\nPreview only. Pending file deletions: 0.\n"
        for output, status in ((blocked, "review"), ("arbitrary output", "failed")):
            with patch.object(preview.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")) as run:
                result = preview.run_preview("apply_account_retention", Path("fixture"), {})
                self.assertEqual(result["result"], status)
                self.assertNotIn("--apply", run.call_args.args[0])
                self.assertNotIn("arbitrary output", str(result))

    def test_independent_previews_continue_after_failure(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            website = root / "releases/1234567/apps/website"
            website.mkdir(parents=True)
            (website / "manage.py").touch()
            with patch.object(preview, "staging_environment", return_value={}), \
                    patch.object(preview, "run_preview", side_effect=[OSError, {"result": "success"}, {"result": "success"}]), \
                    patch.object(preview, "eligible", side_effect=[ValueError, []]):
                statuses = [record["result"] for record in preview.collect_previews(root, "1234567").values()]
        self.assertEqual(statuses, ["failed", "success", "success", "failed", "success"])
