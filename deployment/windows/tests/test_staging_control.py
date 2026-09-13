import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import staging_control as control


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'control/result').mkdir(parents=True)
        (self.root / 'state').mkdir()
        self.initial = dict(schema=1, sequence=0, next_sequence=1, status='idle')
        control.result(self.root, self.initial)

    def payload(self, **changes):
        return json.dumps(dict(schema=1, sequence=1, commit='a'*40, **changes)).encode()

    def status(self):
        return json.loads((self.root / 'control/result/status.json').read_text())

    def test_success_and_replay(self):
        calls = []
        control.consume(self.root, io.BytesIO(self.payload()), lambda c: calls.append(c) or {'commit': c})
        self.assertEqual(self.status()['status'], 'succeeded')
        self.assertEqual(self.status()['next_sequence'], 2)
        with self.assertRaises(ValueError):
            control.consume(self.root, io.BytesIO(self.payload()), calls.append)
        self.assertEqual(len(calls), 1)

    def test_failed_deployment_consumes_identity(self):
        def fail(commit):
            raise RuntimeError('private secret diagnostic')
        with self.assertRaises(RuntimeError):
            control.consume(self.root, io.BytesIO(self.payload()), fail)
        self.assertEqual(self.status()['status'], 'failed')
        self.assertNotIn('private secret', json.dumps(self.status()))
        self.assertEqual(self.status()['next_sequence'], 2)

    def test_crash_never_reexecutes(self):
        control.result(self.root, dict(self.initial, status='running', next_sequence=2))
        control.consume(self.root, io.BytesIO(self.payload()), lambda c: self.fail('replayed'))
        self.assertEqual(self.status()['status'], 'failed')

    def test_malformed_request_reports_rejection(self):
        with self.assertRaises(ValueError):
            control.consume(self.root, io.BytesIO(b'{"command":"evil"}'), lambda c: self.fail('executed'))
        self.assertEqual(self.status()['status'], 'rejected')
        self.assertEqual(self.status()['next_sequence'], 2)

    def test_malformed_and_payload_fields(self):
        for data in (b'{}', b'[]', b'x'*257, b'{"schema":1,"schema":1}',
                     self.payload(path='C:\\production'), self.payload(command='whoami'),
                     self.payload(env={'PATH':'evil'})):
            with self.subTest(data=data), self.assertRaises(ValueError):
                control.request(data)
        for commit in ('../a', 'G:\\GSA', '--help', 'a'*12, 'a'*40+';whoami'):
            with self.assertRaises(ValueError):
                control.request(json.dumps(dict(schema=1, sequence=1, commit=commit)).encode())
        for sequence in (True, 0, -1, 1.5, '1'):
            with self.assertRaises(ValueError):
                control.request(json.dumps(dict(schema=1, sequence=sequence, commit='a'*40)).encode())

    def test_exclusive_handle_prevents_write_and_replace(self):
        path = self.root / 'request.json'
        path.write_bytes(self.payload())
        with control.exclusive_request(path):
            with self.assertRaises(OSError):
                with control.exclusive_request(path, write=True):
                    pass
            other = self.root / 'other'
            other.write_bytes(b'{}')
            with self.assertRaises(OSError):
                other.replace(path)

    def test_concurrent_switch_rejected(self):
        with control.release.switch_lock(self.root):
            with self.assertRaises(RuntimeError):
                with control.release.switch_lock(self.root):
                    pass

    def test_task_boundary(self):
        installer = (SCRIPTS / 'Install-RatRaceStagingStartup.ps1').read_text()
        self.assertIn("-TaskName 'RatRaceStagingDeploy'", installer)
        self.assertIn('-RunLevel Limited', installer)
        self.assertIn('(A;;GRGX;;;$operatorSid)', installer)
        self.assertNotIn('(A;;GA;;;$operatorSid)', installer)
        self.assertIn("'Read,WriteData,Synchronize'", installer)
        submit = (SCRIPTS / 'Submit-RatRaceStagingDeployment.ps1').read_text()
        self.assertNotIn('Register-ScheduledTask', submit)
        self.assertNotIn('RunAs', submit)
        launcher = (SCRIPTS / 'Start-RatRaceStagingDeployment.ps1').read_text()
        self.assertNotIn('releases\\', launcher)
        self.assertIn("@('-I', '-B'", launcher)

    def test_migration_preflight_guards(self):
        script = (SCRIPTS / 'Move-RatRaceStagingHost.ps1').read_text()
        self.assertIn("$Mode = 'Preflight'", script)
        self.assertLess(script.index("if ($Mode -ne 'Provision') { return }"), script.index('New-LocalUser'))
        for guard in ('postmaster.pid', 'ReparsePoint', 'Current release outside staging',
                      'Copy', 'Get-Inventory', '5433,8002'):
            self.assertIn(guard.lower(), script.lower())
        for prohibited in ('Remove-Item', 'Stop-Service', 'Start-Service', 'Register-ScheduledTask'):
            self.assertNotIn(prohibited, script)


if __name__ == '__main__':
    unittest.main()
