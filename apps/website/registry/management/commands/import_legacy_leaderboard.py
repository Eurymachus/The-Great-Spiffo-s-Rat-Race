import hashlib
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from registry.legacy_imports import apply_legacy_import, build_legacy_import_preview
from registry.models import LegacyDataImport


class Command(BaseCommand):
    help = "Validate and optionally import final Legacy Leaderboard and Hall of Fame CSV files."

    def add_arguments(self, parser):
        parser.add_argument("--leaderboard", required=True)
        parser.add_argument("--hall-of-fame", required=True)
        parser.add_argument(
            "--confirm", action="store_true",
            help="Replace the current imported legacy dataset after validation.",
        )

    def handle(self, *args, **options):
        leaderboard_path = Path(options["leaderboard"])
        hall_of_fame_path = Path(options["hall_of_fame"])
        try:
            leaderboard_csv = leaderboard_path.read_text(encoding="utf-8-sig")
            hall_of_fame_csv = hall_of_fame_path.read_text(encoding="utf-8-sig")
            preview = build_legacy_import_preview(leaderboard_csv, hall_of_fame_csv)
        except (OSError, ValueError, ValidationError) as exc:
            message = "; ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
            raise CommandError(message) from exc

        counts = preview["counts"]
        self.stdout.write(
            f"Validated {counts['leaderboard_rows']} leaderboard rows and "
            f"{counts['hall_of_fame_rows']} Hall of Fame rows, producing "
            f"{counts['merged_runs']} merged legacy runs."
        )
        if not options["confirm"]:
            self.stdout.write(self.style.WARNING("Preview only. Re-run with --confirm to import."))
            return

        review = LegacyDataImport.objects.create(
            status=LegacyDataImport.Status.PREVIEW,
            leaderboard_filename=leaderboard_path.name,
            hall_of_fame_filename=hall_of_fame_path.name,
            leaderboard_sha256=hashlib.sha256(leaderboard_csv.encode("utf-8")).hexdigest(),
            hall_of_fame_sha256=hashlib.sha256(hall_of_fame_csv.encode("utf-8")).hexdigest(),
            leaderboard_csv=leaderboard_csv,
            hall_of_fame_csv=hall_of_fame_csv,
            preview=preview,
        )
        apply_legacy_import(review, None)
        self.stdout.write(self.style.SUCCESS(f"Imported {counts['merged_runs']} legacy runs."))
