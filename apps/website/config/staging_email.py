from django.conf import settings

from .graph_email import MicrosoftGraphEmailBackend


class AllowlistedStagingEmailBackend(MicrosoftGraphEmailBackend):
    """Prevent staging from emailing any address outside its explicit allowlist."""

    def send_messages(self, email_messages):
        allowed = settings.STAGING_EMAIL_ALLOWLIST
        for message in email_messages:
            recipients = {
                address.strip().lower()
                for address in message.recipients()
                if address.strip()
            }
            blocked = recipients - allowed
            if blocked:
                raise ValueError(
                    "Staging email recipient is not allowlisted: "
                    + ", ".join(sorted(blocked))
                )
        return super().send_messages(email_messages)
