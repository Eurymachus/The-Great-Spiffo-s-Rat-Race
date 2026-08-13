import json
from unittest.mock import patch

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from .graph_email import MicrosoftGraphEmailBackend


class Response:
    def __init__(self, payload=b""):
        self.payload = payload

    def read(self, *_args):
        return self.payload

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass


@override_settings(
    MICROSOFT_GRAPH_TENANT_ID="tenant",
    MICROSOFT_GRAPH_CLIENT_ID="client",
    MICROSOFT_GRAPH_CLIENT_SECRET="secret",
    MICROSOFT_GRAPH_SENDER="support@tgsrr.com",
    MICROSOFT_GRAPH_REPLY_TO="support@tgsrr.com",
    DEFAULT_FROM_EMAIL="The Great Spiffo's Rat Race <noreply@tgsrr.com>",
)
class MicrosoftGraphEmailBackendTests(SimpleTestCase):
    @patch("config.graph_email.request.urlopen")
    def test_sends_html_email_through_scoped_sender(self, urlopen):
        urlopen.side_effect = [
            Response(b'{"access_token":"token"}'),
            Response(),
        ]
        message = EmailMultiAlternatives(
            subject="Welcome",
            body="Plain text",
            to=["rat@example.com"],
        )
        message.attach_alternative("<p>Welcome</p>", "text/html")

        sent = MicrosoftGraphEmailBackend().send_messages([message])

        self.assertEqual(sent, 1)
        token_request, mail_request = [call.args[0] for call in urlopen.call_args_list]
        self.assertIn("tenant/oauth2/v2.0/token", token_request.full_url)
        self.assertEqual(
            mail_request.full_url,
            "https://graph.microsoft.com/v1.0/users/support%40tgsrr.com/sendMail",
        )
        self.assertEqual(mail_request.headers["Authorization"], "Bearer token")
        payload = json.loads(mail_request.data)
        self.assertEqual(payload["message"]["body"]["contentType"], "HTML")
        self.assertEqual(
            payload["message"]["toRecipients"][0]["emailAddress"]["address"],
            "rat@example.com",
        )
        self.assertEqual(
            payload["message"]["from"]["emailAddress"],
            {
                "name": "The Great Spiffo's Rat Race",
                "address": "noreply@tgsrr.com",
            },
        )
        self.assertEqual(
            payload["message"]["replyTo"][0]["emailAddress"]["address"],
            "support@tgsrr.com",
        )
