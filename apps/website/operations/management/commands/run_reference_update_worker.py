import time
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand

from operations.queue import claim_next_reference_update
from operations.reference_update import run_reference_update
from operations.decompilation import run_decompilation
from operations.models import ReferenceUpdateJob
from operations.catalogue_review import generate_catalogue_review
from operations.models import CatalogueImportReview, PZWikiArtworkSyncJob
from operations.worker_health import WorkerHeartbeat
from operations.process_control import stop_requested
from operations.leaderboard_publish import tick as publish_daily_leaderboard
from django.db import transaction
from django.utils import timezone


@transaction.atomic
def claim_next_catalogue_review():
    review = (
        CatalogueImportReview.objects.select_for_update()
        .filter(status=CatalogueImportReview.Status.QUEUED)
        .order_by("requested_at", "pk")
        .first()
    )
    if review:
        review.status = CatalogueImportReview.Status.GENERATING
        review.started_at = timezone.now()
        review.save(update_fields=("status", "started_at"))
    return review


@transaction.atomic
def claim_next_wiki_icon_sync():
    job = (
        PZWikiArtworkSyncJob.objects.select_for_update()
        .select_related("catalogue_review")
        .filter(status=PZWikiArtworkSyncJob.Status.QUEUED)
        .order_by("requested_at", "pk")
        .first()
    )
    if job:
        if job.catalogue_review.status != CatalogueImportReview.Status.APPROVED:
            job.status = PZWikiArtworkSyncJob.Status.CANCELLED
            job.finished_at = timezone.now()
            job.summary = "Cancelled because the catalogue review is no longer approved."
            job.save(update_fields=("status", "finished_at", "summary"))
            return None
        job.status = PZWikiArtworkSyncJob.Status.RUNNING
        job.started_at = timezone.now()
        job.summary = "Reconciling supported catalogue artwork with PZWiki."
        job.save(update_fields=("status", "started_at", "summary"))
    return job


def run_wiki_icon_sync(job):
    class LiveOutput(StringIO):
        def write(self, text):
            if text.strip():
                job.log_output = (job.log_output + f"[{timezone.now():%H:%M:%S} UTC] {text.strip()}\n")[-65536:]
                PZWikiArtworkSyncJob.objects.filter(pk=job.pk).update(log_output=job.log_output)
            result = super().write(text)
            if self.tell() > 65536:
                tail = self.getvalue()[-65536:]
                self.seek(0)
                self.truncate()
                super().write(tail)
            return result

    output = LiveOutput()
    output.write("Starting PZWiki artwork reconciliation.\n")
    unavailable_artwork = []
    try:
        call_command(
            "import_pzwiki_icons",
            game_version=job.catalogue_review.game_version,
            report_output=unavailable_artwork,
            stdout=output,
            stderr=output,
            no_color=True,
        )
    except Exception as exc:
        job.status = PZWikiArtworkSyncJob.Status.FAILED
        job.summary = f"PZWiki artwork reconciliation failed: {exc}"
    else:
        job.status = PZWikiArtworkSyncJob.Status.COMPLETE
        output_lines = [
            line.strip()
            for line in output.getvalue().splitlines()
            if line.strip()
        ]
        job.summary = (
            output_lines[-1]
            if output_lines
            else "PZWiki artwork reconciliation completed."
        )
    output.write(job.summary + "\n")
    job.unavailable_artwork = unavailable_artwork
    job.finished_at = timezone.now()
    job.save(
        update_fields=(
            "status",
            "summary",
            "unavailable_artwork",
            "finished_at",
        )
    )


class Command(BaseCommand):
    help = "Process queued Project Zomboid reference updates."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--poll-interval", type=float, default=5.0)

    def handle(self, *args, **options):
        once = options["once"]
        interval = max(options["poll_interval"], 0.25)
        heartbeat = WorkerHeartbeat()
        heartbeat.start()
        self.stdout.write("Reference update worker ready.")
        try:
            while not stop_requested():
                job = claim_next_reference_update()
                if job:
                    self.stdout.write(f"Processing reference update #{job.pk}.")
                    if job.operation == ReferenceUpdateJob.Operation.DECOMPILE:
                        run_decompilation(job)
                    else:
                        run_reference_update(job)
                    job.refresh_from_db()
                    self.stdout.write(
                        f"Reference update #{job.pk}: {job.get_status_display()}."
                    )
                else:
                    review = claim_next_catalogue_review()
                    if review:
                        self.stdout.write(f"Generating catalogue review #{review.pk}.")
                        generate_catalogue_review(review)
                        review.refresh_from_db()
                        self.stdout.write(
                            f"Catalogue review #{review.pk}: {review.get_status_display()}."
                        )
                    else:
                        artwork_job = claim_next_wiki_icon_sync()
                        if artwork_job:
                            self.stdout.write(
                                f"Processing PZWiki artwork sync #{artwork_job.pk}."
                            )
                            run_wiki_icon_sync(artwork_job)
                            artwork_job.refresh_from_db()
                            self.stdout.write(
                                f"PZWiki artwork sync #{artwork_job.pk}: "
                                f"{artwork_job.get_status_display()}."
                            )
                if stop_requested():
                    return
                publish_daily_leaderboard()
                if once:
                    return
                time.sleep(interval)
        finally:
            heartbeat.stop()
