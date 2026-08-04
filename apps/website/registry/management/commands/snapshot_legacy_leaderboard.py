from django.core.management.base import BaseCommand, CommandError

from registry.legacy_leaderboard import DEFAULT_SNAPSHOT, build_snapshot, download_workbook, write_snapshot


class Command(BaseCommand):
    help = "Download and package the Historical Leaderboard worksheet as a deployment snapshot."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=str(DEFAULT_SNAPSHOT))

    def handle(self, *args, **options):
        try:
            snapshot = build_snapshot(download_workbook())
            path = write_snapshot(snapshot, options["output"])
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Wrote {snapshot['entry_count']} legacy entries to {path}."))
