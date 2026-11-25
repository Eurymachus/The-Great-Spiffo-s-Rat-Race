from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import host_artifacts as artifacts


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = artifacts.utcnow()

    def artifact(self, name, age, kind='backup'):
        target = self.root / name
        target.mkdir()
        (target / 'payload').write_text('fixture')
        manifest = dict(format=artifacts.FORMAT, kind=kind,
                        completed_at=(self.now - timedelta(days=age)).isoformat(),
                        files=artifacts.inventory(target))
        (target / artifacts.MANIFEST).write_text(json.dumps(manifest))
        return target

    def test_preview_never_deletes_and_apply_only_expires_recognized_packages(self):
        old = self.artifact('old', 31)
        recent = self.artifact('recent', 29)
        unknown = self.root / 'old-unmarked'
        unknown.mkdir()
        self.assertEqual(artifacts.expire(self.root, now=self.now), [old])
        self.assertTrue(old.exists())
        self.assertEqual(artifacts.expire(self.root, apply=True, now=self.now), [old])
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(unknown.exists())

    def test_log_expiry_is_90_days_and_unmarked_active_logs_survive(self):
        old = self.artifact('closed-old', 91, 'closed-routine-log')
        self.artifact('closed-recent', 89, 'closed-routine-log')
        active = self.root / 'web.log'
        active.write_text('active')
        self.assertEqual(artifacts.eligible(self.root, self.now), [old])
        self.assertTrue(active.exists())

    def test_package_and_root_holds_prevent_deletion(self):
        old = self.artifact('held', 31)
        (old / '.hold').touch()
        self.assertEqual(artifacts.eligible(self.root, self.now), [])
        (old / '.hold').unlink()
        (self.root / '.hold').touch()
        self.assertEqual(artifacts.expire(self.root, True, self.now), [])
        self.assertTrue(old.exists())

    def test_modified_or_added_content_blocks_entire_plan(self):
        old = self.artifact('old', 31)
        (old / 'unregistered').write_text('must survive')
        with self.assertRaises(ValueError):
            artifacts.expire(self.root, True, self.now)
        self.assertTrue(old.exists())

    def test_modified_payload_is_not_silently_removed(self):
        old = self.artifact('old', 31)
        (old / 'payload').write_text('changed')
        with self.assertRaises(ValueError):
            artifacts.eligible(self.root, self.now)

    def test_reparse_attribute_fails_closed(self):
        class ReparseStat:
            st_mode = 0
            st_file_attributes = 0x400
        with patch.object(Path, 'lstat', return_value=ReparseStat()):
            with self.assertRaises(ValueError):
                artifacts.checked(self.root)

    def test_environment_parser_handles_quotes_and_rejects_duplicates(self):
        env = self.root / 'fixture.env'
        env.write_text('POSTGRES_PASSWORD="a:b=c"\n')
        self.assertEqual(artifacts.read_environment(env)['POSTGRES_PASSWORD'], 'a:b=c')
        env.write_text('POSTGRES_DB=a\nPOSTGRES_DB=b\n')
        with self.assertRaises(ValueError):
            artifacts.read_environment(env)

    def capture_setup(self):
        parent = self.root / 'backups'
        source = self.root / 'media'
        parent.mkdir()
        source.mkdir()
        (source / 'asset').write_text('media fixture')
        env = self.root / 'fixture.env'
        env.write_text('POSTGRES_HOST=127.0.0.1\nPOSTGRES_PORT=55432\nPOSTGRES_DB=fixture\n'
                       'POSTGRES_USER=fixture\nPOSTGRES_PASSWORD=test:only\\value\n')
        return parent, source, env

    @patch.object(artifacts, 'protect')
    def test_capture_manifest_and_password_file_lifecycle(self, protect):
        parent, source, env = self.capture_setup()
        def run(args, **kwargs):
            protect.assert_called_once()
            if args[0].endswith('pg_dump.exe'):
                self.assertNotIn('PGPASSWORD', kwargs['env'])
                passfile = Path(kwargs['env']['PGPASSFILE'])
                self.assertIn(r'test\:only\\value', passfile.read_text())
                destination = next(arg[7:] for arg in args if arg.startswith('--file='))
                Path(destination).write_bytes(b'dump fixture')
            else:
                kwargs['stdout'].write(b'catalogue fixture')
        with patch.object(artifacts.subprocess, 'run', side_effect=run):
            target = artifacts.capture(parent, env, self.root, [source], 'fixture-release')
        self.assertFalse((target / '.pgpass').exists())
        self.assertTrue((target / artifacts.MANIFEST).exists())
        self.assertEqual((target / 'files-0/asset').read_text(), 'media fixture')
        self.assertEqual(artifacts.eligible(parent, self.now + timedelta(days=32)), [target])

    @patch.object(artifacts, 'protect')
    def test_failed_dump_keeps_incomplete_package_and_removes_password_file(self, protect):
        parent, source, env = self.capture_setup()
        with patch.object(artifacts.subprocess, 'run', side_effect=OSError('fixture failure')):
            with self.assertRaises(OSError):
                artifacts.capture(parent, env, self.root, [source], 'fixture')
        target = next(parent.iterdir())
        self.assertFalse((target / '.pgpass').exists())
        self.assertFalse((target / artifacts.MANIFEST).exists())
        self.assertEqual(artifacts.eligible(parent, self.now + timedelta(days=40)), [])

    def test_overlapping_source_and_destination_rejected_before_creation(self):
        parent, source, env = self.capture_setup()
        with self.assertRaises(ValueError):
            artifacts.capture(parent, env, self.root, [self.root], 'fixture')
        self.assertEqual(list(parent.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
