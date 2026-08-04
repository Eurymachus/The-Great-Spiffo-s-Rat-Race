import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from registry.legacy_leaderboard import DEFAULT_SNAPSHOT
from registry.models import LegacyLeaderboardEntry


class Command(BaseCommand):
    help = "Idempotently import the packaged Legacy Hall of Fame snapshot."

    def add_arguments(self, parser):
        parser.add_argument("--input", default=str(DEFAULT_SNAPSHOT))

    def handle(self, *args, **options):
        path = Path(options["input"])
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            if snapshot.get("schema_version") != 1:
                raise ValueError("Unsupported legacy snapshot schema.")
            captured_at = datetime.fromisoformat(snapshot["captured_at"])
            entries = snapshot["entries"]
            if snapshot.get("entry_count") != len(entries):
                raise ValueError("Legacy snapshot entry count does not match its contents.")
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise CommandError(str(exc)) from exc
        created = updated = 0
        with transaction.atomic():
            for item in entries:
                _, was_created = LegacyLeaderboardEntry.objects.update_or_create(
                    source_key=item["source_key"],
                    defaults={
                        **{key: value for key, value in item.items() if key != "source_key"},
                        "snapshot_id": snapshot["snapshot_id"],
                        "snapshot_captured_at": captured_at,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(f"Imported {created} new and updated {updated} legacy entries."))
