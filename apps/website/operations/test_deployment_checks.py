from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from operations.deployment_checks import executable_available, production_deployment_checks


class ExecutableAvailabilityTests(SimpleTestCase):
    def test_accepts_existing_explicit_file(self):
        with patch("pathlib.Path.is_file", return_value=True):
            self.assertTrue(executable_available("C:/tools/steamcmd.exe"))

    def test_uses_path_lookup_for_command_name(self):
        with patch("operations.deployment_checks.shutil.which", return_value="java"):
            self.assertTrue(executable_available("java"))

    def test_rejects_missing_command(self):
        with patch("operations.deployment_checks.shutil.which", return_value=None):
            self.assertFalse(executable_available("missing-command"))

    def test_deployment_checks_require_disabled_asgi_persistence(self):
        with patch.object(
            settings, "DATABASES", {"default": {"CONN_MAX_AGE": 0}}
        ):
            self.assertTrue(
                production_deployment_checks()["ASGI database connections"]
            )

    def test_deployment_checks_reject_persistent_asgi_connections(self):
        with patch.object(
            settings, "DATABASES", {"default": {"CONN_MAX_AGE": 60}}
        ):
            self.assertFalse(
                production_deployment_checks()["ASGI database connections"]
            )


class DeploymentRepositoryConfigurationTests(SimpleTestCase):
    def test_asgi_environment_templates_disable_persistent_connections(self):
        repository_root = Path(__file__).resolve().parents[3]
        files = (
            repository_root / ".env.example",
            repository_root / "deployment/windows/New-RatRaceStagingEnvironment.ps1",
            repository_root / "deployment/windows/New-RatRaceAcceptanceEnvironment.ps1",
        )

        for path in files:
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertIn("POSTGRES_CONN_MAX_AGE=0", content)
                self.assertNotIn("POSTGRES_CONN_MAX_AGE=60", content)

    def test_windows_release_preparation_reconciles_roles_after_migrations(self):
        repository_root = Path(__file__).resolve().parents[3]
        script = (
            repository_root
            / "deployment/windows/Prepare-RatRaceRelease.ps1"
        ).read_text(encoding="utf-8")

        migrate_position = script.index("manage.py migrate --noinput")
        roles_position = script.index("manage.py bootstrap_roles")
        static_position = script.index("manage.py collectstatic --noinput")

        self.assertLess(migrate_position, roles_position)
        self.assertLess(roles_position, static_position)

        staging_installer = (
            repository_root
            / "deployment/windows/Install-RatRaceStagingStartup.ps1"
        ).read_text(encoding="utf-8")
        preparation_position = staging_installer.index("& $preparer")
        installation_position = staging_installer.index("& $installer")

        self.assertLess(preparation_position, installation_position)


class ProductionDeploymentCommandTests(SimpleTestCase):
    @patch(
        "operations.management.commands.check_production_deployment."
        "evaluate_production_deployment_checks"
    )
    def test_reports_success(self, evaluate):
        evaluate.return_value = {"database": True, "cache": True}
        output = StringIO()

        call_command("check_production_deployment", stdout=output)

        self.assertIn("[PASS] database", output.getvalue())
        self.assertIn("Production deployment check passed.", output.getvalue())

    @patch(
        "operations.management.commands.check_production_deployment."
        "evaluate_production_deployment_checks"
    )
    def test_fails_with_component_names(self, evaluate):
        evaluate.return_value = {"database": True, "cache": False}

        with self.assertRaisesMessage(CommandError, "cache"):
            call_command("check_production_deployment", stdout=StringIO())
