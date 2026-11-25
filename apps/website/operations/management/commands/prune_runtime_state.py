from django.core.management.base import BaseCommand
from django.utils import timezone

from operations.models import RateLimitBucket


class Command(BaseCommand):
    help = "Preview expired database rate-limit buckets; --apply removes only expired buckets."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        expired = RateLimitBucket.objects.filter(expires_at__lte=timezone.now())
        if options["apply"]:
            deleted, _ = expired.delete()
            self.stdout.write(f"Deleted {deleted} expired rate-limit bucket(s).")
        else:
            self.stdout.write(f"Preview only: {expired.count()} expired rate-limit bucket(s).")
