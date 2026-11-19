from django.core.management.base import BaseCommand, CommandError

from operations.leaderboard_publish import configuration, enqueue
from operations.models import DailyLeaderboardSchedule


class Command(BaseCommand):
    help = "Configure the hosted DEV daily leaderboard, optionally queueing a test."

    def add_arguments(self, parser):
        parser.add_argument("--enable", action="store_true")
        parser.add_argument("--disable", action="store_true")
        parser.add_argument("--hour", type=int, default=9)
        parser.add_argument("--minute", type=int, default=0)
        parser.add_argument("--timezone", default="Europe/London")
        parser.add_argument("--enqueue", action="store_true")

    def handle(self, *args, **options):
        if options["enable"] and options["disable"]:
            raise CommandError("Choose enable or disable.")
        if not options["disable"]:
            try:
                configuration()
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
        schedule, _ = DailyLeaderboardSchedule.objects.get_or_create(pk=1)
        schedule.hour = options["hour"]
        schedule.minute = options["minute"]
        schedule.timezone_name = options["timezone"]
        if options["enable"] or options["disable"]:
            schedule.enabled = options["enable"]
        schedule.full_clean()
        schedule.save()
        self.stdout.write(f"Daily schedule: enabled={schedule.enabled}, {schedule.hour:02}:{schedule.minute:02} {schedule.timezone_name}.")
        if options["enqueue"]:
            job = enqueue()
            self.stdout.write(f"Job {job.pk}: {job.get_status_display()}.")
