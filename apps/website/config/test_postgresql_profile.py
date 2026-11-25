import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class PostgreSQLProfileSafetyTests(SimpleTestCase):
    def probe(self, **settings):
        environment = {key: value for key, value in os.environ.items() if not key.startswith('RR_TEST_POSTGRES_')}
        environment.update(settings)
        return subprocess.run(
            [sys.executable, '-c', 'import config.settings_test_postgresql'],
            cwd=Path(__file__).resolve().parents[1], env=environment,
            capture_output=True, timeout=15,
        )

    def test_requires_isolated_acknowledgement(self):
        self.assertNotEqual(self.probe().returncode, 0)

    def test_rejects_live_and_staging_ports(self):
        for port in ('5432', '5433', '0', '65536'):
            with self.subTest(port=port):
                self.assertNotEqual(self.probe(RR_TEST_POSTGRES_ISOLATED='yes', RR_TEST_POSTGRES_PORT=port).returncode, 0)

    def test_accepts_explicit_isolated_profile_without_connecting(self):
        self.assertEqual(self.probe(RR_TEST_POSTGRES_ISOLATED='yes', RR_TEST_POSTGRES_PORT='55433',
                                    RR_TEST_POSTGRES_USER='fixture', RR_TEST_POSTGRES_PASSWORD='fixture').returncode, 0)
