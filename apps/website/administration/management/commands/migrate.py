"""Refuse pre-launch databases instead of pretending they match the baseline."""
from django.core.management.base import CommandError
from django.core.management.commands.migrate import Command as DjangoMigrateCommand
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder


BASELINE_APPS = frozenset({
    "administration", "branding", "operations", "pages", "registry", "zomboid_catalogue",
})


def require_launch_database(connection):
    applied = MigrationRecorder(connection).applied_migrations()
    legacy_apps = {
        app for app, _ in applied
        if app in BASELINE_APPS and (app, "0001_launch_schema") not in applied
    }
    if legacy_apps:
        raise CommandError(
            "This database uses pre-launch migration history. The launch baseline "
            "requires a fresh application database. Back up credentials, encryption "
            "keys and data before a separately scoped reset. Do not fake migrations. "
            "Affected apps: " + ", ".join(sorted(legacy_apps))
        )


class Command(DjangoMigrateCommand):
    def handle(self, *args, **options):
        require_launch_database(connections[options["database"]])
        return super().handle(*args, **options)
