import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


def validate_turnstile(token, remote_ip):
    if not token or len(token) > 2048:
        return False

    payload = urlencode(
        {
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": token,
            "remoteip": remote_ip,
        }
    ).encode("utf-8")
    request = Request(settings.TURNSTILE_VERIFY_URL, data=payload, method="POST")
    try:
        with urlopen(request, timeout=settings.TURNSTILE_TIMEOUT_SECONDS) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return False
    return result.get("success") is True
