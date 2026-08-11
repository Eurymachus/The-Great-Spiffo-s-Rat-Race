from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from operations.deployment_checks import executable_available


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
