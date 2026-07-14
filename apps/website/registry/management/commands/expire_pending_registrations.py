from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from registry.models import Participant


class Command(BaseCommand):
    help = "Expire pending registrations whose latest verification email is too old."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(
            seconds=settings.PENDING_REGISTRATION_MAX_AGE
        )
        expired = Participant.objects.filter(
            status=Participant.Status.PENDING,
            verification_sent_at__lt=cutoff,
        ).update(status=Participant.Status.EXPIRED)
        self.stdout.write(self.style.SUCCESS(f"Expired {expired} registration(s)."))
