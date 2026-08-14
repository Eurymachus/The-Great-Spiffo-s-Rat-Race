from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings
from unittest.mock import patch

from .graph_email import MicrosoftGraphEmailBackend
from .staging_email import AllowlistedStagingEmailBackend


@override_settings(
    STAGING_EMAIL_ALLOW_ALL=False,
    STAGING_EMAIL_ALLOWLIST={"allowed@example.com"},
)
class AllowlistedStagingEmailBackendTests(SimpleTestCase):
    def test_rejects_non_allowlisted_recipient_before_graph(self):
        message = EmailMessage(to=["blocked@example.com"])

        with self.assertRaisesRegex(ValueError, "blocked@example.com"):
            AllowlistedStagingEmailBackend().send_messages([message])

    def test_allows_only_allowlisted_recipients(self):
        message = EmailMessage(to=["allowed@example.com"])
        backend = AllowlistedStagingEmailBackend()

        with patch.object(
            MicrosoftGraphEmailBackend, "send_messages", return_value=1
        ) as send_messages:
            self.assertEqual(backend.send_messages([message]), 1)
            send_messages.assert_called_once_with([message])

    @override_settings(STAGING_EMAIL_ALLOW_ALL=True)
    def test_allows_any_recipient_when_explicitly_enabled(self):
        message = EmailMessage(to=["new-tester@example.com"])
        backend = AllowlistedStagingEmailBackend()

        with patch.object(
            MicrosoftGraphEmailBackend, "send_messages", return_value=1
        ) as send_messages:
            self.assertEqual(backend.send_messages([message]), 1)
            send_messages.assert_called_once_with([message])
