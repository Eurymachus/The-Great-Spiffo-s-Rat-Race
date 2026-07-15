from django.core.mail import send_mail
from django.conf import settings

from .models import Participant


def send_verification_email(participant: Participant, verification_url: str) -> None:
    send_mail(
        subject=f"Verify your {settings.SITE_SHORT_TITLE} nickname",
        message=(
            f"Hello {participant.nickname},\n\n"
            f"Confirm your email address and reserve your {settings.SITE_SHORT_TITLE} nickname by "
            f"opening this link:\n\n{verification_url}\n\n"
            "This link expires after 24 hours. If you did not request this, you "
            "can ignore this email.\n\n"
            f"{settings.SITE_FULL_TITLE}\n"
            f"{settings.SITE_TAGLINE}"
        ),
        from_email=None,
        recipient_list=[participant.email],
    )


def send_password_reset_email(participant: Participant, reset_url: str) -> None:
    send_mail(
        subject=f"Reset your {settings.SITE_SHORT_TITLE} password",
        message=(
            f"Hello {participant.nickname},\n\n"
            f"A password reset was requested for your {settings.SITE_SHORT_TITLE} account. Choose "
            f"a new password by opening this link:\n\n{reset_url}\n\n"
            "This link expires after one hour and can only be used once. If you "
            "did not request this, you can safely ignore this email. Your current "
            "password has not been changed.\n\n"
            f"{settings.SITE_FULL_TITLE}\n"
            f"{settings.SITE_TAGLINE}"
        ),
        from_email=None,
        recipient_list=[participant.email],
    )
