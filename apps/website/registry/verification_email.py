from django.core.mail import send_mail
from django.conf import settings

from branding.models import SiteBranding
from .models import Participant


def current_brand_titles():
    brand = SiteBranding.current()
    if brand:
        return brand.full_title, brand.short_title, brand.tagline
    return settings.SITE_FULL_TITLE, settings.SITE_SHORT_TITLE, settings.SITE_TAGLINE


def send_verification_email(participant: Participant, verification_url: str) -> None:
    full_title, short_title, tagline = current_brand_titles()
    send_mail(
        subject=f"Verify your {short_title} nickname",
        message=(
            f"Hello {participant.nickname},\n\n"
            f"Confirm your email address and reserve your {short_title} nickname by "
            f"opening this link:\n\n{verification_url}\n\n"
            "This link expires after 24 hours. If you did not request this, you "
            "can ignore this email.\n\n"
            f"{full_title}\n"
            f"{tagline}"
        ),
        from_email=None,
        recipient_list=[participant.email],
    )


def send_password_reset_email(participant: Participant, reset_url: str) -> None:
    full_title, short_title, tagline = current_brand_titles()
    send_mail(
        subject=f"Reset your {short_title} password",
        message=(
            f"Hello {participant.nickname},\n\n"
            f"A password reset was requested for your {short_title} account. Choose "
            f"a new password by opening this link:\n\n{reset_url}\n\n"
            "This link expires after one hour and can only be used once. If you "
            "did not request this, you can safely ignore this email. Your current "
            "password has not been changed.\n\n"
            f"{full_title}\n"
            f"{tagline}"
        ),
        from_email=None,
        recipient_list=[participant.email],
    )
