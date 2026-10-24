from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from registry.models import LegacyRun, LegacyRunClaim, LegacyRunSubmission


class Command(BaseCommand):
    help = "Preview or reset Rat Race 1.0 runs, claims and submissions on staging only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm", action="store_true",
            help="Delete all staging Rat Race 1.0 runs, claims and submissions.",
        )

    def handle(self, *args, **options):
        if getattr(settings, "STAGING_ENVIRONMENT", False) is not True:
            raise CommandError("Rat Race 1.0 rehearsal reset is restricted to staging.")

        with transaction.atomic():
            # Serialize against changes to existing runs during the reset.
            # Operators must pause staging imports and submissions for this operation.
            runs = LegacyRun.objects.all()
            if options["confirm"]:
                list(runs.select_for_update().values_list("pk", flat=True))
            self.stdout.write(
                f"Rat Race 1.0 reset: {runs.count()} runs, "
                f"{LegacyRunClaim.objects.count()} claims, "
                f"{LegacyRunSubmission.objects.count()} submissions."
            )
            self.stdout.write(
                "Preserved: accounts, platform connections and credentials, "
                "Rat Race 2.0 runs, import audit records and notifications."
            )
            if not options["confirm"]:
                self.stdout.write("Preview only. Re-run with --confirm to reset.")
                return
            # Only the run-owned 1.0 claims and submissions cascade from these rows.
            runs.delete()

        self.stdout.write(self.style.SUCCESS(
            "Rat Race 1.0 rehearsal reset complete. Upload fresh CSVs to rehearse again."
        ))
