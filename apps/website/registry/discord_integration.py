from administration.provider_credentials import get_provider_credentials, ProviderConfigurationError
import json
import re
import secrets
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
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
    try:
        credentials = _provider_credentials()
    except DiscordIntegrationError:
        return False
    client_id = credentials.client_id
    return bool(
        re.fullmatch(r"[1-9][0-9]{16,19}", client_id or "")
        and int(client_id) < 2**64
        and credentials.client_secret.strip()
        and settings.STREAMING_TOKEN_ENCRYPTION_KEY.strip()
        and _discord_callback_matches_public_origin()
    )


def _discord_callback_matches_public_origin():
    from administration.provider_credentials import callback_matches
    return callback_matches('discord', _provider_credentials().redirect_uri)


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
    credentials = _provider_credentials()
    if not discord_is_configured():
        raise DiscordIntegrationError("Discord connection is not configured.")
    state = secrets.token_urlsafe(32)
    request.session[DISCORD_STATE_SESSION_KEY] = {
        "value": state,
        "created_at": timezone.now().timestamp(),
    }
    return f"{DISCORD_AUTHORIZE_URL}?{urlencode({
        'response_type': 'code',
        'client_id': credentials.client_id,
        'redirect_uri': credentials.redirect_uri,
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
    credentials = _provider_credentials(required=True)
    return _json_request(
        DISCORD_TOKEN_URL,
        data={
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": credentials.redirect_uri,
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
    credentials = _provider_credentials()
    token = decrypt_token(account.encrypted_access_token)
    if token and credentials.client_id.strip() and credentials.client_secret.strip():
        try:
            _json_request(
                DISCORD_REVOKE_URL,
                data={
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "token": token,
                    "token_type_hint": "access_token",
                },
            )
        except DiscordIntegrationError:
            pass


def _provider_credentials(required=False):
    try:
        credentials = get_provider_credentials("discord")
        if required and not (credentials.client_id and credentials.client_secret):
            raise ProviderConfigurationError()
        return credentials
    except ProviderConfigurationError:
        raise DiscordIntegrationError("Discord connection configuration is unavailable.") from None
