from datetime import timedelta
from pathlib import Path
import json
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import host_artifacts
import run_logged_process


class LoggedProcessTests(unittest.TestCase):
    @patch.object(run_logged_process, 'protect')
    def test_cooperative_child_drains_tail_and_records_sealed_segments(self, protect):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'logs'
            root.mkdir()
            control = Path(directory) / 'control'
            code = ("import os,time,pathlib; p=pathlib.Path(os.environ['RR_PROCESS_STOP_FILE']); "
                    "token=os.environ['RR_PROCESS_STOP_TOKEN']; print('started',flush=True)\n"
                    "while not p.exists() or p.read_text()!=token: time.sleep(.02)\n"
                    "print('final output',flush=True)\n")
            results = []
            thread = threading.Thread(target=lambda: results.append(run_logged_process.run(
                [sys.executable, '-u', '-c', code], root, 'worker', control_root=control)))
            thread.start()
            deadline = time.monotonic() + 10
            while not (control / 'worker.json').exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue((control / 'worker.json').exists())
            descriptor = json.loads((control / 'worker.json').read_text())
            request = control / (descriptor['token'] + '.stop')
            request.write_text('stale-token')
            time.sleep(.1)
            self.assertTrue(thread.is_alive())
            request.write_text(descriptor['token'])
            thread.join(10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(results, [0])
            receipt = json.loads((control / 'worker.json').read_text())
            self.assertEqual((receipt['state'], receipt['exit_code']), ('exited', 0))
            self.assertTrue(receipt['closed_segments'])
            output = b''.join((p / 'stdout.log').read_bytes() for p in root.iterdir())
            self.assertIn(b'final output', output)
            self.assertEqual(len(host_artifacts.eligible(root, host_artifacts.utcnow() + timedelta(days=91))), len(receipt['closed_segments']))

    @patch.object(run_logged_process, 'protect')
    def test_rotation_preserves_both_streams_and_exit_status(self, protect):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = "import sys; sys.stdout.write('A'*100); sys.stderr.write('B'*70); sys.exit(7)"
            self.assertEqual(run_logged_process.run([sys.executable, '-c', code], root, 'web', limit=32), 7)
            folders = sorted(root.iterdir())
            self.assertEqual(len(folders), 6)
            self.assertEqual(sum(len((p / 'stdout.log').read_bytes()) for p in folders), 100)
            self.assertEqual(sum(len((p / 'stderr.log').read_bytes()) for p in folders), 70)
            self.assertEqual(len(host_artifacts.eligible(root, host_artifacts.utcnow() + timedelta(days=91))), 6)
            self.assertEqual(protect.call_count, 6)

    @patch.object(run_logged_process, 'protect')
    def test_active_segment_has_no_expiry_manifest(self, protect):
        with tempfile.TemporaryDirectory() as directory:
            logs = run_logged_process.Segments(directory, 'worker')
            logs.write('stdout', b'active')
            self.assertEqual(host_artifacts.eligible(directory, host_artifacts.utcnow() + timedelta(days=100)), [])
            logs.close()
            self.assertEqual(len(host_artifacts.eligible(directory, host_artifacts.utcnow() + timedelta(days=100))), 1)

    @patch.object(run_logged_process, 'protect', side_effect=OSError('ACL fixture'))
    def test_acl_failure_leaves_no_sealed_log(self, protect):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                run_logged_process.run([sys.executable, '-c', "print('fixture')"], directory, 'web')
            self.assertEqual(host_artifacts.eligible(directory, host_artifacts.utcnow() + timedelta(days=100)), [])
