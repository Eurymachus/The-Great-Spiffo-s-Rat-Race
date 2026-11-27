"""Acceptance for the fresh-install baseline, not obsolete development upgrades."""
from importlib import import_module
from unittest.mock import patch

from django.apps import apps
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TestCase

from .management.commands.migrate import require_launch_database


class LaunchBaselineTests(TestCase):
    def test_setup_seed_has_no_accounts_credentials_or_run_history(self):
        for label in (
            "registry.Participant", "registry.LegacyRun", "registry.LegacyRunClaim",
            "registry.LegacyRunSubmission", "registry.ChallengeRun", "registry.RunSubmission",
            "registry.StreamingAccount", "registry.Notification",
            "administration.ProviderConfiguration",
        ):
            with self.subTest(model=label):
                self.assertEqual(apps.get_model(label).objects.count(), 0)
        self.assertEqual(apps.get_model("registry.LegacySavedView").objects.count(), 5)
        self.assertEqual(apps.get_model("branding.WebsiteTheme").objects.count(), 3)
        self.assertTrue(apps.get_model("operations.ReferenceSource").objects.filter(app_id=108600).exists())

    def test_seed_and_role_bootstrap_can_be_repeated(self):
        seed = import_module("administration.migrations.0002_launch_seed")
        from types import SimpleNamespace
        models = [model for model in apps.get_models() if model._meta.app_label in {
            "administration", "branding", "operations", "pages", "registry", "zomboid_catalogue",
        }]
        before = {model: model.objects.count() for model in models}
        seed.install_seed(apps, SimpleNamespace(connection=connection))
        seed.install_seed(apps, SimpleNamespace(connection=connection))
        self.assertEqual(before, {model: model.objects.count() for model in models})
        call_command("bootstrap_roles", verbosity=0)
        call_command("bootstrap_roles", verbosity=0)
        self.assertEqual(apps.get_model("registry.Participant").objects.count(), 0)

    @patch("administration.management.commands.migrate.MigrationRecorder")
    def test_old_history_is_rejected_before_migration(self, recorder):
        recorder.return_value.applied_migrations.return_value = {("registry", "0085_example"): object()}
        with self.assertRaisesMessage(CommandError, "fresh application database"):
            require_launch_database(connection)

    @patch("administration.management.commands.migrate.MigrationRecorder")
    def test_baseline_and_future_migrations_are_accepted(self, recorder):
        for history in ({}, {("registry", "0001_launch_schema"): object(), ("registry", "0002_future_contract"): object()}):
            recorder.return_value.applied_migrations.return_value = history
            require_launch_database(connection)
