import base64
import json
from email.utils import parseaddr
from urllib import error, parse, request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class MicrosoftGraphEmailBackend(BaseEmailBackend):
    """Send Django email messages through Microsoft Graph app authentication."""

    def _token(self):
        body = parse.urlencode(
            {
                "client_id": settings.MICROSOFT_GRAPH_CLIENT_ID,
                "client_secret": settings.MICROSOFT_GRAPH_CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }
        ).encode()
        response = request.urlopen(
            request.Request(
                f"https://login.microsoftonline.com/{settings.MICROSOFT_GRAPH_TENANT_ID}/oauth2/v2.0/token",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ),
            timeout=20,
        )
        return json.load(response)["access_token"]

    @staticmethod
    def _recipients(addresses):
        return [
            {"emailAddress": {"address": parseaddr(address)[1]}}
            for address in addresses
        ]

    def _payload(self, message):
        body = message.body
        content_type = "Text"
        for alternative in getattr(message, "alternatives", ()):
            content, mimetype = alternative[:2]
            if mimetype == "text/html":
                body, content_type = content, "HTML"
                break
        graph_message = {
            "subject": message.subject,
            "body": {"contentType": content_type, "content": body},
            "from": {
                "emailAddress": {
                    "name": parseaddr(message.from_email)[0],
                    "address": parseaddr(message.from_email)[1],
                }
            },
            "toRecipients": self._recipients(message.to),
            "ccRecipients": self._recipients(message.cc),
            "bccRecipients": self._recipients(message.bcc),
            "replyTo": self._recipients(
                message.reply_to or [settings.MICROSOFT_GRAPH_REPLY_TO]
            ),
        }
        attachments = []
        for attachment in message.attachments:
            name = getattr(attachment, "name", attachment[0])
            content = getattr(attachment, "content", attachment[1])
            mimetype = getattr(attachment, "mimetype", attachment[2])
            if isinstance(content, str):
                content = content.encode()
            attachments.append(
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": name,
                    "contentType": mimetype,
                    "contentBytes": base64.b64encode(content).decode("ascii"),
                }
            )
        if attachments:
            graph_message["attachments"] = attachments
        return {"message": graph_message, "saveToSentItems": True}

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        token = self._token()
        endpoint = (
            "https://graph.microsoft.com/v1.0/users/"
            f"{parse.quote(settings.MICROSOFT_GRAPH_SENDER)}/sendMail"
        )
        sent = 0
        for message in email_messages:
            try:
                request.urlopen(
                    request.Request(
                        endpoint,
                        data=json.dumps(self._payload(message)).encode(),
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        method="POST",
                    ),
                    timeout=30,
                ).close()
                sent += 1
            except error.HTTPError:
                if not self.fail_silently:
                    raise
        return sent
