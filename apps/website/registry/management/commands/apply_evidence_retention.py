from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from registry.evidence_retention import retire_run_evidence, retire_workshop_notes
from registry.models import LegacyRun, WorkshopMod
from registry.retention import AccountDeletionBlocked


class Command(BaseCommand):
    help = "Preview two-year first-release evidence expiry; --apply clears eligible text while preserving results and rulings."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        counts = Counter()
        for queryset, operation in (
            (LegacyRun.objects.exclude(lifecycle=LegacyRun.Lifecycle.ACTIVE), retire_run_evidence),
            (WorkshopMod.objects.exclude(ruling=WorkshopMod.Ruling.PENDING), retire_workshop_notes),
        ):
            for pk in list(queryset.order_by("pk").values_list("pk", flat=True)):
                try:
                    counts[operation(pk, apply=options["apply"], now=now)] += 1
                except AccountDeletionBlocked:
                    counts["blocked"] += 1
        self.stdout.write(("Applied: " if options["apply"] else "Preview only: ") + ", ".join(f"{key}={counts[key]}" for key in ("eligible", "retained", "held", "changed", "blocked", "empty")))
        if options["apply"] and (counts["blocked"] or counts["changed"]):
            raise CommandError("Evidence retention requires review or retry. No personal identifiers were logged.")
