import json
import secrets
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import StreamingMedia


TWITCH_AUTHORIZE_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
TWITCH_REVOKE_URL = "https://id.twitch.tv/oauth2/revoke"
TWITCH_VIDEOS_URL = "https://api.twitch.tv/helix/videos"
TWITCH_CLIPS_URL = "https://api.twitch.tv/helix/clips"
TWITCH_STATE_SESSION_KEY = "twitch_oauth_state"


class TwitchIntegrationError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def twitch_is_configured():
    return all(
        (
            settings.TWITCH_CLIENT_ID,
            settings.TWITCH_CLIENT_SECRET,
            settings.TWITCH_REDIRECT_URI,
            settings.STREAMING_TOKEN_ENCRYPTION_KEY,
        )
    )


def _fernet():
    try:
        return Fernet(settings.STREAMING_TOKEN_ENCRYPTION_KEY.encode("ascii"))
    except (AttributeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "STREAMING_TOKEN_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc


def encrypt_token(value):
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii") if value else ""


def decrypt_token(value):
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TwitchIntegrationError("The stored Twitch credential could not be decrypted.") from exc


def begin_twitch_authorization(request):
    if not twitch_is_configured():
        raise TwitchIntegrationError("Twitch connection is not configured.")
    state = secrets.token_urlsafe(32)
    request.session[TWITCH_STATE_SESSION_KEY] = {
        "value": state,
        "created_at": timezone.now().timestamp(),
    }
    return f"{TWITCH_AUTHORIZE_URL}?{urlencode({
        'response_type': 'code',
        'client_id': settings.TWITCH_CLIENT_ID,
        'redirect_uri': settings.TWITCH_REDIRECT_URI,
        'state': state,
        'force_verify': 'true',
    })}"


def consume_twitch_state(request, supplied_state):
    stored = request.session.pop(TWITCH_STATE_SESSION_KEY, None)
    if not stored or not secrets.compare_digest(stored.get("value", ""), supplied_state or ""):
        raise TwitchIntegrationError("The Twitch connection request could not be verified.")
    if timezone.now().timestamp() - stored.get("created_at", 0) > 600:
        raise TwitchIntegrationError("The Twitch connection request expired. Please try again.")


def _json_request(url, *, data=None, headers=None):
    encoded = urlencode(data).encode("ascii") if data is not None else None
    request = Request(url, data=encoded, headers=headers or {})
    try:
        with urlopen(request, timeout=settings.TWITCH_HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise TwitchIntegrationError(
            "Twitch could not complete the request. Please try again.",
            status=exc.code,
        ) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise TwitchIntegrationError("Twitch could not complete the request. Please try again.") from exc


def exchange_twitch_code(code):
    return _json_request(
        TWITCH_TOKEN_URL,
        data={
            "client_id": settings.TWITCH_CLIENT_ID,
            "client_secret": settings.TWITCH_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.TWITCH_REDIRECT_URI,
        },
    )


def validate_twitch_token(access_token):
    result = _json_request(
        TWITCH_VALIDATE_URL,
        headers={"Authorization": f"OAuth {access_token}"},
    )
    if result.get("client_id") != settings.TWITCH_CLIENT_ID or not result.get("user_id"):
        raise TwitchIntegrationError("Twitch returned an invalid account identity.")
    return result


def refresh_twitch_token(account):
    refresh_token = decrypt_token(account.encrypted_refresh_token)
    if not refresh_token:
        raise TwitchIntegrationError("Reconnect Twitch to renew access.", status=401)
    try:
        token_data = _json_request(
            TWITCH_TOKEN_URL,
            data={
                "client_id": settings.TWITCH_CLIENT_ID,
                "client_secret": settings.TWITCH_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        identity = validate_twitch_token(token_data["access_token"])
    except TwitchIntegrationError as exc:
        if exc.status not in {400, 401}:
            raise
        raise TwitchIntegrationError(
            "Twitch access has been revoked. Reconnect Twitch to restore access.",
            status=401,
        ) from exc
    except KeyError as exc:
        raise TwitchIntegrationError(
            "Twitch returned an incomplete credential response. Please try again."
        ) from exc
    apply_twitch_credentials(account, token_data, identity)
    return token_data["access_token"]


def get_valid_twitch_token(account):
    token = decrypt_token(account.encrypted_access_token)
    if not token:
        raise TwitchIntegrationError("Reconnect Twitch to restore access.", status=401)
    if (
        account.token_validated_at
        and account.token_validated_at >= timezone.now() - timedelta(hours=1)
    ):
        return token
    try:
        identity = validate_twitch_token(token)
    except TwitchIntegrationError as exc:
        if exc.status != 401:
            raise
        return refresh_twitch_token(account)
    account.token_validated_at = timezone.now()
    account.token_expires_at = timezone.now() + timedelta(
        seconds=identity.get("expires_in", 0)
    )
    account.status = account.Status.CONNECTED
    account.save(update_fields=("token_validated_at", "token_expires_at", "status"))
    return token


def _duration_seconds(value):
    total = 0
    number = ""
    for character in value or "":
        if character.isdigit():
            number += character
        elif number and character in "hms":
            total += int(number) * {"h": 3600, "m": 60, "s": 1}[character]
            number = ""
    return total or None


def _twitch_api(url, token, params):
    return _json_request(
        f"{url}?{urlencode(params)}",
        headers={
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.TWITCH_CLIENT_ID,
        },
    ).get("data", [])


def refresh_twitch_media(account):
    token = get_valid_twitch_token(account)
    try:
        videos = _twitch_api(
            TWITCH_VIDEOS_URL, token,
            {"user_id": account.channel_identity, "type": "archive", "first": 20},
        )
        clips = _twitch_api(
            TWITCH_CLIPS_URL, token,
            {"broadcaster_id": account.channel_identity, "first": 20},
        )
    except TwitchIntegrationError as exc:
        if exc.status != 401:
            raise
        token = refresh_twitch_token(account)
        videos = _twitch_api(
            TWITCH_VIDEOS_URL, token,
            {"user_id": account.channel_identity, "type": "archive", "first": 20},
        )
        clips = _twitch_api(
            TWITCH_CLIPS_URL, token,
            {"broadcaster_id": account.channel_identity, "first": 20},
        )
    for item in videos:
        StreamingMedia.objects.update_or_create(
            account=account,
            kind=StreamingMedia.Kind.VIDEO,
            provider_media_id=item["id"],
            defaults={
                "parent_media_id": "",
                "title": item.get("title", ""),
                "canonical_url": item["url"],
                "thumbnail_url": item.get("thumbnail_url", "")
                .replace("%{width}", "640")
                .replace("%{height}", "360"),
                "published_at": parse_datetime(item.get("published_at", "")),
                "duration_seconds": _duration_seconds(item.get("duration")),
                "metadata_snapshot": item,
            },
        )
    for item in clips:
        StreamingMedia.objects.update_or_create(
            account=account,
            kind=StreamingMedia.Kind.CLIP,
            provider_media_id=item["id"],
            defaults={
                "parent_media_id": item.get("video_id", ""),
                "title": item.get("title", ""),
                "canonical_url": item["url"],
                "thumbnail_url": item.get("thumbnail_url", ""),
                "published_at": parse_datetime(item.get("created_at", "")),
                "duration_seconds": round(item.get("duration", 0)) or None,
                "vod_offset_seconds": item.get("vod_offset"),
                "metadata_snapshot": item,
            },
        )
    return len(videos), len(clips)


def apply_twitch_credentials(account, token_data, identity):
    account.provider_identity = identity["user_id"]
    account.channel_identity = identity["user_id"]
    account.display_name = identity["login"]
    account.channel_url = f"https://www.twitch.tv/{identity['login']}"
    account.granted_scopes = (
        identity.get("scopes") or token_data.get("scope") or []
    )
    account.encrypted_access_token = encrypt_token(token_data["access_token"])
    account.encrypted_refresh_token = encrypt_token(token_data.get("refresh_token", ""))
    account.token_expires_at = timezone.now() + timedelta(
        seconds=identity.get("expires_in", token_data.get("expires_in", 0))
    )
    account.token_validated_at = timezone.now()
    account.refreshed_at = timezone.now()
    account.status = account.Status.CONNECTED
    account.save()


def revoke_twitch_account(account):
    token = decrypt_token(account.encrypted_access_token)
    if token and twitch_is_configured():
        try:
            _json_request(
                TWITCH_REVOKE_URL,
                data={"client_id": settings.TWITCH_CLIENT_ID, "token": token},
            )
        except TwitchIntegrationError:
            pass
