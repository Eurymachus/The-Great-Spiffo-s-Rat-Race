from django.core.management.base import BaseCommand

from operations.models import ReferenceSource, ReferenceUpdateJob
from operations.queue import enqueue_reference_update


class Command(BaseCommand):
    help = "Queue a Project Zomboid reference update for the background worker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--trigger",
            choices=[choice.value for choice in ReferenceUpdateJob.Trigger],
            default=ReferenceUpdateJob.Trigger.SCHEDULED,
        )

    def handle(self, *args, **options):
        source, _ = ReferenceSource.objects.get_or_create(app_id=108600)
        job, created = enqueue_reference_update(
            source, trigger=options["trigger"]
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Queued reference update #{job.pk}."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Reference update #{job.pk} is already {job.get_status_display().lower()}."
                )
            )
