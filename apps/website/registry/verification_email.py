from django.core.mail import send_mail

from .models import Participant


def send_verification_email(participant: Participant, verification_url: str) -> None:
    send_mail(
        subject="Verify your Rat Race nickname",
        message=(
            f"Hello {participant.nickname},\n\n"
            "Confirm your email address and reserve your Rat Race nickname by "
            f"opening this link:\n\n{verification_url}\n\n"
            "This link expires after 24 hours. If you did not request this, you "
            "can ignore this email.\n\n"
            "The Great Spiffo's Rat Race\n"
            "The official Rat Race challenge"
        ),
        from_email=None,
        recipient_list=[participant.email],
    )


def send_password_reset_email(participant: Participant, reset_url: str) -> None:
    send_mail(
        subject="Reset your Rat Race password",
        message=(
            f"Hello {participant.nickname},\n\n"
            "A password reset was requested for your Rat Race account. Choose "
            f"a new password by opening this link:\n\n{reset_url}\n\n"
            "This link expires after one hour and can only be used once. If you "
            "did not request this, you can safely ignore this email. Your current "
            "password has not been changed.\n\n"
            "The Great Spiffo's Rat Race\n"
            "The official Rat Race challenge"
        ),
        from_email=None,
        recipient_list=[participant.email],
    )
