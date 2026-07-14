from django.conf import settings
from django.core import signing

from .models import Participant


VERIFICATION_SALT = "registry.email-verification.v1"


def create_verification_token(participant: Participant) -> str:
    return signing.dumps(
        {
            "participant_id": str(participant.id),
            "email": participant.normalized_email,
        },
        salt=VERIFICATION_SALT,
        compress=True,
    )


def read_verification_token(token: str) -> dict:
    return signing.loads(
        token,
        salt=VERIFICATION_SALT,
        max_age=settings.VERIFICATION_LINK_MAX_AGE,
    )
