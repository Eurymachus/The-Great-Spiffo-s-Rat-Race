from administration.provider_credentials import get_provider_credentials, ProviderConfigurationError
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


def validate_turnstile(token, remote_ip):
    if not token or len(token) > 2048:
        return False

    try:
        credentials = get_provider_credentials('turnstile')
    except ProviderConfigurationError:
        return False
    if not credentials.client_secret:
        return False
    payload = urlencode(
        {
            "secret": credentials.client_secret,
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


def turnstile_site_key():
    try:
        return get_provider_credentials('turnstile').client_id
    except ProviderConfigurationError:
        return ''
