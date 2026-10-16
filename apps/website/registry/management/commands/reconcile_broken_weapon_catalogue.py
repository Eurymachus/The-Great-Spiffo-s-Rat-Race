from django.core.management.base import BaseCommand
from django.db import transaction

from registry.models import RunDailyMetric, RunStatisticMetric
from zomboid_catalogue.resolver import resolve_identifier


class Command(BaseCommand):
    help = "Link unresolved broken-weapon item IDs; dry run unless --apply is supplied."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        groups = (
            RunStatisticMetric.objects.filter(summary__kind="broken_weapons", dimension="item"),
            RunDailyMetric.objects.filter(kind="broken_weapon"),
        )
        total = 0
        for group in groups:
            missing = group.filter(primary_catalogue_entry__isnull=True)
            for raw_id in missing.values_list("raw_primary_id", flat=True).distinct():
                # Exact stable identifiers only: historical evidence is never guessed.
                entry = resolve_identifier("item", raw_id)
                if entry is None or entry.stable_id != raw_id:
                    continue
                rows = missing.filter(raw_primary_id=raw_id)
                count = rows.count()
                if options["apply"]:
                    rows.update(primary_catalogue_entry=entry)
                total += count
                self.stdout.write(f"{raw_id}: {count} links -> entry {entry.pk}")
        self.stdout.write(f"{'Applied' if options['apply'] else 'Dry run'}: {total} links; raw IDs and values unchanged.")
