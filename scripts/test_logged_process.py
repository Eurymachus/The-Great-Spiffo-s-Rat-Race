from datetime import timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import host_artifacts
import run_logged_process


class LoggedProcessTests(unittest.TestCase):
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
