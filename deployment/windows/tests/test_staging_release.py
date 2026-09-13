import importlib.util
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta

SCRIPT = Path(__file__).resolve().parents[1] / "staging_release.py"
spec = importlib.util.spec_from_file_location("staging_release", SCRIPT)
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)


class FakeHost:
    def __init__(self, failure=None):
        self.failure = failure
        self.events = []

    def preflight(self):
        self.events.append("preflight")

    def prepare(self, selected, directory):
        self.events.append("prepare")
        if self.failure == "prepare":
            raise RuntimeError("preparation failed")

    def stop(self):
        self.events.append("stop")

    def start(self):
        self.events.append("start")

    def verify(self, selected, directory, started):
        self.events.append("verify:" + selected["release"])
        if self.failure in {"readiness", "heartbeat"} and selected["release"].startswith("b"):
            raise RuntimeError(self.failure + " failed")


class StagingReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "state").mkdir()
        (self.root / "releases").mkdir()
        self.old = self.make_release("a")
        self.new = self.make_release("b")
        staging.atomic_pointer(self.root, self.old)

    def make_release(self, char):
        commit = char * 40
        name = commit[:12]
        directory = self.root / "releases" / name
        directory.mkdir()
        files = {}
        for name_in_release in ("apps/website/manage.py", "apps/website/config/asgi.py", "apps/website/config/settings_windows_staging.py"):
            path = directory / name_in_release
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"# release fixture\n")
            files[name_in_release] = hashlib.sha256(path.read_bytes()).hexdigest()
        (directory / staging.MANIFEST).write_text(json.dumps({"schema": 1, "commit": commit, "files": files}))
        return {"schema": 1, "release": name, "commit": commit}

    def test_path_traversal_and_outside_root(self):
        for name in ("../production", "..\\GSA", "G:\\RatRace\\production", "/tmp/release", "aaaaaaa/../../", "", "abcdefg"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                staging.release(self.root, name)
        with self.assertRaises(ValueError):
            staging.confined(self.root.parent / "GSA", self.root)

    def test_malformed_missing_and_wrong_identity(self):
        path = self.root / "releases" / self.new["release"] / staging.MANIFEST
        for value in ("[]", "{", '{"schema":1}', json.dumps({"schema": 1, "commit": "c" * 40, "files": {}})):
            path.write_text(value)
            with self.assertRaises((ValueError, KeyError)):
                staging.release(self.root, self.new["release"])
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            staging.release(self.root, self.new["release"])

    def test_hash_and_inventory_tampering(self):
        directory = self.root / "releases" / self.new["release"]
        (directory / "extra.py").write_text("unexpected")
        with self.assertRaises(ValueError):
            staging.release(self.root, self.new["release"])
        (directory / "extra.py").unlink()
        (directory / "apps/website/manage.py").write_text("changed")
        with self.assertRaises(ValueError):
            staging.release(self.root, self.new["release"])

    def test_preparation_failure_leaves_pointer_and_processes_unchanged(self):
        host = FakeHost("prepare")
        before = (self.root / "state/active-release.json").read_bytes()
        with self.assertRaises(RuntimeError):
            staging.switch(self.root, self.new["release"], host)
        self.assertEqual(before, (self.root / "state/active-release.json").read_bytes())
        self.assertEqual(host.events, ["preflight", "prepare"])

    def test_atomic_replacement_preserves_old_on_replace_failure(self):
        with patch.object(staging.os, "replace", side_effect=OSError("locked")):
            with self.assertRaises(OSError):
                staging.atomic_pointer(self.root, self.new)
        self.assertEqual(staging.active(self.root)[0], self.old)
        self.assertFalse(list((self.root / "state").glob("*.tmp")))
        replace = staging.os.replace
        def check(source, destination):
            self.assertEqual(Path(source).parent, Path(destination).parent)
            self.assertEqual(staging.read_json(source), self.new)
            self.assertEqual(staging.read_json(destination), self.old)
            replace(source, destination)
        with patch.object(staging.os, "replace", side_effect=check):
            staging.atomic_pointer(self.root, self.new)
        self.assertEqual(staging.active(self.root)[0], self.new)

    def test_successful_cutover(self):
        host = FakeHost()
        self.assertEqual(staging.switch(self.root, self.new["release"], host), self.new)
        self.assertEqual(host.events, ["preflight", "prepare", "stop", "start", "verify:" + self.new["release"]])
        self.assertEqual(staging.active(self.root)[0], self.new)

    def test_failed_readiness_rolls_back(self):
        self.check_rollback("readiness")

    def test_failed_worker_heartbeat_rolls_back(self):
        self.check_rollback("heartbeat")

    def check_rollback(self, failure):
        host = FakeHost(failure)
        with self.assertRaisesRegex(RuntimeError, "previous release restored"):
            staging.switch(self.root, self.new["release"], host)
        self.assertEqual(staging.active(self.root)[0], self.old)
        self.assertEqual(host.events[-3:], ["stop", "start", "verify:" + self.old["release"]])

    def test_rollback_failure_is_explicit(self):
        host = FakeHost()
        host.verify = lambda *args: (_ for _ in ()).throw(RuntimeError("unhealthy"))
        with self.assertRaisesRegex(RuntimeError, "ROLLBACK FAILED"):
            staging.switch(self.root, self.new["release"], host)

    def test_permanent_task_actions_and_privilege_boundary(self):
        installer = SCRIPT.with_name("Install-RatRaceStagingStartup.ps1").read_text()
        self.assertIn("-RunLevel Limited", installer)
        self.assertNotIn("-RunLevel Highest", installer)
        self.assertNotIn("-ReleaseRoot", installer)
        self.assertIn("Start-RatRaceStagingProcess.ps1", installer)
        self.assertIn("GRGX", installer)
        control = SCRIPT.with_name("Staging-TaskControl.ps1").read_text()
        self.assertNotIn("Register-ScheduledTask", control)
        self.assertNotIn("Set-ScheduledTask", control)
        self.assertIn("CreationDate -eq", control)

    def test_production_and_gsa_isolation(self):
        self.assertEqual(str(staging.ROOT), r"G:\RatRace_StagingSecured")
        self.assertEqual(staging.TASKS, ("RatRaceStagingWeb", "RatRaceStagingWorker"))
        for file in ("Staging-TaskControl.ps1", "Install-RatRaceStagingStartup.ps1"):
            code = SCRIPT.with_name(file).read_text()
            self.assertNotIn("Register-Service", code)
            self.assertNotIn("Stop-Service", code)
            self.assertNotIn("pg_ctl", code)
        config = self.root / "config"
        config.mkdir()
        (config / "staging.env").write_text("DJANGO_SETTINGS_MODULE=config.settings_windows_staging\nPOSTGRES_HOST=127.0.0.1\nPOSTGRES_PORT=5432\n")
        with self.assertRaisesRegex(ValueError, "5433"):
            staging.environment(self.root, self.new)

    def test_health_adapter_rejects_stale_wrong_release_and_wrong_worker(self):
        started = datetime.now(timezone.utc)
        base = {"release_id": self.new["commit"], "process_id": 42, "recorded_at": (started + timedelta(seconds=1)).isoformat()}
        for change in ({"release_id": "old"}, {"process_id": 99}, {"recorded_at": (started - timedelta(seconds=1)).isoformat()}):
            with self.subTest(change=change):
                self.check_health_adapter({**base, **change}, started, False)
        self.check_health_adapter(base, started, True)

    def check_health_adapter(self, heartbeat, started, success):
        import io
        health = io.BytesIO(json.dumps({"release": self.new["commit"], "checks": {"reference_worker": True}}).encode())
        health.status = 200
        host = staging.WindowsHost(self.root)
        with patch.object(host, "control", return_value={"worker_pid": 42, "web_pid": 41}), \
             patch.object(staging, "environment", return_value={}), \
             patch.object(staging.urllib.request, "build_opener") as opener, \
             patch.object(staging.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(heartbeat))), \
             patch.object(staging.time, "monotonic", side_effect=[0, 1, 181]), \
             patch.object(staging.time, "sleep"):
            opener.return_value.open.return_value = health
            if success:
                host.verify(self.new, self.root, started)
            else:
                with self.assertRaisesRegex(RuntimeError, "Cutover verification failed"):
                    host.verify(self.new, self.root, started)

    def test_preparation_command_order_and_release_environment(self):
        host = staging.WindowsHost(self.root)
        env = {"STATIC_ROOT": str(self.root / "runtime/static/new"), "RELEASE_ID": self.new["commit"]}
        with patch.object(staging, "environment", return_value=env), patch.object(staging.subprocess, "run") as run:
            host.prepare(self.new, self.root)
        self.assertEqual([call.args[0][2:] for call in run.call_args_list], [
            ['migrate', '--noinput'], ['bootstrap_roles'], ['collectstatic', '--noinput'],
            ['check', '--deploy', '--fail-level', 'WARNING'], ['check_production_deployment']])
        for call in run.call_args_list:
            self.assertEqual(call.kwargs['env']['RELEASE_ID'], self.new['commit'])
            self.assertTrue(call.kwargs['check'])

    def test_concurrent_switch_lock(self):
        with staging.switch_lock(self.root):
            with self.assertRaisesRegex(RuntimeError, "Another staging switch"):
                with staging.switch_lock(self.root):
                    self.fail("Lock permitted concurrent deployment")

    def test_publish_uses_committed_archive(self):
        import io
        import zipfile
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            for name in ('apps/website/manage.py', 'apps/website/config/asgi.py', 'apps/website/config/settings_windows_staging.py'):
                archive.writestr(name, '# exported\n')
        commit = 'c' * 40
        with patch.object(staging.subprocess, 'check_output', side_effect=[commit, data.getvalue()]):
            name = staging.publish(self.root, Path('source'), commit)
        self.assertEqual(staging.release(self.root, name)[0]['commit'], commit)


if __name__ == "__main__":
    unittest.main()
