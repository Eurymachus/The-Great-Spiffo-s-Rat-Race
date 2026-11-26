from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from host_artifacts import FORMAT, inventory
from staging_backup import database_check, verify_latest


class BackupChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime.now(timezone.utc)

    def package(self, hours):
        target = self.root / ('backup-' + str(hours))
        target.mkdir()
        (target / 'database.dump').write_text('fixture')
        (target / 'artifact.json').write_text(json.dumps(dict(
            format=FORMAT, kind='backup', completed_at=(self.now-timedelta(hours=hours)).isoformat(),
            files=inventory(target))))
        return target

    def test_fresh_and_incomplete_package(self):
        good = self.package(1)
        (self.root / 'backup-incomplete').mkdir()
        self.assertEqual(verify_latest(self.root, self.now), good)

    def test_missing_stale_and_future(self):
        with self.assertRaises(ValueError):
            verify_latest(self.root, self.now)
        self.package(31)
        with self.assertRaises(ValueError):
            verify_latest(self.root, self.now)
        self.package(-1)
        with self.assertRaises(ValueError):
            verify_latest(self.root, self.now)

    def test_corrupt_newest_does_not_fall_back_to_good_old_backup(self):
        self.package(2)
        newest = self.package(1)
        (newest / 'database.dump').write_text('changed')
        with self.assertRaises(ValueError):
            verify_latest(self.root, self.now)

    def test_active_catalogue_generation_blocks_capture(self):
        driver = MagicMock()
        cursor = driver.connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(0,), (0,), (0,), (1,)]
        values = dict(POSTGRES_HOST='127.0.0.1', POSTGRES_PORT='5433',
                      POSTGRES_DB='fixture', POSTGRES_USER='fixture', POSTGRES_PASSWORD='fixture')
        with patch.dict('sys.modules', psycopg=driver):
            with self.assertRaisesRegex(ValueError, 'queue is not idle'):
                database_check(values, stopped=True)
        query = cursor.execute.call_args.args[0]
        self.assertIn('operations_catalogueimportreview', query)
        self.assertIn("'generating'", query)


if __name__ == '__main__':
    unittest.main()
