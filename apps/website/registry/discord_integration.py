import json
import re
import secrets
from datetime import timedelta
from ipaddress import ip_address
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from .streaming import decrypt_token, encrypt_token


DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_REVOKE_URL = "https://discord.com/api/oauth2/token/revoke"
DISCORD_CURRENT_USER_URL = "https://discord.com/api/v10/users/@me"
DISCORD_STATE_SESSION_KEY = "discord_oauth_state"


class DiscordIntegrationError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def discord_is_configured():
    client_id = settings.DISCORD_CLIENT_ID
    return bool(
        re.fullmatch(r"[1-9][0-9]{16,19}", client_id or "")
        and int(client_id) < 2**64
        and settings.DISCORD_CLIENT_SECRET.strip()
        and settings.STREAMING_TOKEN_ENCRYPTION_KEY.strip()
        and _discord_callback_matches_public_origin()
    )


def _discord_callback_matches_public_origin():
    public_url = settings.SITE_PUBLIC_URL
    if any(character.isspace() or ord(character) < 32 for character in public_url):
        return False
    try:
        origin = urlsplit(public_url)
        hostname, port = origin.hostname, origin.port
    except ValueError:
        return False
    if (
        not hostname
        or origin.username is not None
        or any(character in origin.netloc for character in r"\%")
        or origin.netloc.endswith(":")
        or port == 0
        or public_url not in (f"{origin.scheme}://{origin.netloc}", f"{origin.scheme}://{origin.netloc}/")
    ):
        return False
    try:
        ip_address(hostname)
    except ValueError:
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*", hostname):
            return False
    if origin.scheme != "https" and not (
        origin.scheme == "http" and settings.DEBUG
        and hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        return False
    expected = f"{origin.scheme}://{origin.netloc}{reverse('registry:discord_callback')}"
    return settings.DISCORD_REDIRECT_URI == expected


def _json_request(url, *, data=None, headers=None):
    encoded = urlencode(data).encode("ascii") if data is not None else None
    request = Request(
        url,
        data=encoded,
        headers={"User-Agent": "TGSRR-Website/1.0", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=settings.DISCORD_HTTP_TIMEOUT_SECONDS) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except HTTPError as exc:
        raise DiscordIntegrationError(
            "Discord could not complete the request. Please try again.",
            status=exc.code,
        ) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise DiscordIntegrationError(
            "Discord could not complete the request. Please try again."
        ) from exc


def begin_discord_authorization(request):
    if not discord_is_configured():
        raise DiscordIntegrationError("Discord connection is not configured.")
    state = secrets.token_urlsafe(32)
    request.session[DISCORD_STATE_SESSION_KEY] = {
        "value": state,
        "created_at": timezone.now().timestamp(),
    }
    return f"{DISCORD_AUTHORIZE_URL}?{urlencode({
        'response_type': 'code',
        'client_id': settings.DISCORD_CLIENT_ID,
        'redirect_uri': settings.DISCORD_REDIRECT_URI,
        'scope': 'identify',
        'state': state,
        'prompt': 'consent',
    })}"


def consume_discord_state(request, supplied_state):
    stored = request.session.pop(DISCORD_STATE_SESSION_KEY, None)
    if not stored or not secrets.compare_digest(
        stored.get("value", ""), supplied_state or ""
    ):
        raise DiscordIntegrationError(
            "The Discord connection request could not be verified."
        )
    if timezone.now().timestamp() - stored.get("created_at", 0) > 600:
        raise DiscordIntegrationError(
            "The Discord connection request expired. Please try again."
        )


def exchange_discord_code(code):
    return _json_request(
        DISCORD_TOKEN_URL,
        data={
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.DISCORD_REDIRECT_URI,
        },
    )


def fetch_discord_identity(access_token):
    identity = _json_request(
        DISCORD_CURRENT_USER_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if not identity.get("id") or not identity.get("username"):
        raise DiscordIntegrationError("Discord returned an invalid account identity.")
    return identity


def apply_discord_credentials(account, token_data, identity):
    account.provider_identity = identity["id"]
    account.channel_identity = identity["id"]
    account.display_name = identity.get("global_name") or identity["username"]
    account.channel_url = f"https://discord.com/users/{identity['id']}"
    account.granted_scopes = str(token_data.get("scope", "identify")).split()
    account.provider_metadata = identity
    account.encrypted_access_token = encrypt_token(token_data["access_token"])
    account.encrypted_refresh_token = encrypt_token(token_data.get("refresh_token", ""))
    account.token_expires_at = timezone.now() + timedelta(
        seconds=int(token_data.get("expires_in", 0))
    )
    account.token_validated_at = timezone.now()
    account.refreshed_at = timezone.now()
    account.status = account.Status.CONNECTED
    account.save()


def revoke_discord_account(account):
    token = decrypt_token(account.encrypted_access_token)
    if token and settings.DISCORD_CLIENT_ID.strip() and settings.DISCORD_CLIENT_SECRET.strip():
        try:
            _json_request(
                DISCORD_REVOKE_URL,
                data={
                    "client_id": settings.DISCORD_CLIENT_ID,
                    "client_secret": settings.DISCORD_CLIENT_SECRET,
                    "token": token,
                    "token_type_hint": "access_token",
                },
            )
        except DiscordIntegrationError:
            pass
