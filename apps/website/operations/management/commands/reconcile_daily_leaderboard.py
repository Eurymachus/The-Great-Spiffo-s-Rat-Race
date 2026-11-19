from django.core.management.base import BaseCommand, CommandError

from operations.leaderboard_publish import reconcile
from operations.models import DailyLeaderboardJob


class Command(BaseCommand):
    help = "Verify an interrupted DEV leaderboard upload by downloading the Unlisted test item."

    def add_arguments(self, parser):
        parser.add_argument("job_id", type=int)

    def handle(self, *args, **options):
        try:
            job = reconcile(options["job_id"])
        except DailyLeaderboardJob.DoesNotExist:
            raise CommandError("No interrupted upload found for that job.") from None
        except (OSError, ValueError, RuntimeError) as exc:
            raise CommandError(f"Reconciliation could not verify the upload ({type(exc).__name__}).") from None
        self.stdout.write(self.style.SUCCESS(f"Job {job.pk}: {job.summary}"))
