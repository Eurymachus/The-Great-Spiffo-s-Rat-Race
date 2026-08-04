import json
import logging
import secrets
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .streaming import decrypt_token, encrypt_token


logger = logging.getLogger(__name__)


YOUTUBE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_STATE_SESSION_KEY = "youtube_oauth_state"
YOUTUBE_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/youtube.readonly",
)


class YouTubeIntegrationError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def youtube_is_configured():
    return all(
        (
            settings.YOUTUBE_CLIENT_ID,
            settings.YOUTUBE_CLIENT_SECRET,
            settings.YOUTUBE_REDIRECT_URI,
            settings.STREAMING_TOKEN_ENCRYPTION_KEY,
        )
    )


def _json_request(url, *, data=None, headers=None):
    encoded = urlencode(data).encode("ascii") if data is not None else None
    request = Request(
        url,
        data=encoded,
        headers={"User-Agent": "TGSRR-Website/1.0", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=settings.YOUTUBE_HTTP_TIMEOUT_SECONDS) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except HTTPError as exc:
        error_reason = ""
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
            error_details = error_payload.get("error", {}).get("errors", [])
            if error_details:
                error_reason = error_details[0].get("reason", "")
        except (AttributeError, UnicodeDecodeError, ValueError):
            pass
        logger.warning(
            "YouTube API request failed with HTTP %s and reason %s.",
            exc.code,
            error_reason or "unknown",
        )
        if error_reason in {"accessNotConfigured", "serviceDisabled"}:
            message = (
                "YouTube Data API v3 is not enabled for this Google Cloud project. "
                "Enable it, wait a few minutes, then connect again."
            )
        elif error_reason in {"insufficientPermissions", "forbidden"}:
            message = (
                "Google did not grant permission to read this YouTube channel. "
                "Please connect again and approve YouTube access."
            )
        elif error_reason in {"dailyLimitExceeded", "quotaExceeded"}:
            message = "The YouTube API quota is currently exhausted. Please try again later."
        else:
            message = "YouTube could not complete the request. Please try again."
        raise YouTubeIntegrationError(
            message,
            status=exc.code,
        ) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise YouTubeIntegrationError(
            "YouTube could not complete the request. Please try again."
        ) from exc


def begin_youtube_authorization(request):
    if not youtube_is_configured():
        raise YouTubeIntegrationError("YouTube connection is not configured.")
    state = secrets.token_urlsafe(32)
    request.session[YOUTUBE_STATE_SESSION_KEY] = {
        "value": state,
        "created_at": timezone.now().timestamp(),
    }
    params = {
        "response_type": "code",
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
        "scope": " ".join(YOUTUBE_SCOPES),
        "state": state,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    return f"{YOUTUBE_AUTHORIZE_URL}?{urlencode(params)}"


def consume_youtube_state(request, supplied_state):
    stored = request.session.pop(YOUTUBE_STATE_SESSION_KEY, None)
    if not stored or not secrets.compare_digest(
        stored.get("value", ""), supplied_state or ""
    ):
        raise YouTubeIntegrationError(
            "The YouTube connection request could not be verified."
        )
    if timezone.now().timestamp() - stored.get("created_at", 0) > 600:
        raise YouTubeIntegrationError(
            "The YouTube connection request expired. Please try again."
        )


def exchange_youtube_code(code):
    return _json_request(
        YOUTUBE_TOKEN_URL,
        data={
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
        },
    )


def fetch_google_identity(access_token):
    identity = _json_request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if not identity.get("sub"):
        raise YouTubeIntegrationError("Google returned an invalid account identity.")
    return identity


def fetch_youtube_channel(access_token):
    query = urlencode({"part": "snippet", "mine": "true", "maxResults": 1})
    response = _json_request(
        f"{YOUTUBE_CHANNELS_URL}?{query}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    items = response.get("items") or []
    if not items or not items[0].get("id"):
        raise YouTubeIntegrationError(
            "No YouTube channel was found for the selected Google account."
        )
    channel = items[0]
    if not channel.get("snippet", {}).get("title"):
        raise YouTubeIntegrationError("YouTube returned an invalid channel identity.")
    return channel


def refresh_youtube_token(account):
    refresh_token = decrypt_token(account.encrypted_refresh_token)
    if not refresh_token:
        raise YouTubeIntegrationError("Reconnect YouTube to renew access.", status=401)
    token_data = _json_request(
        YOUTUBE_TOKEN_URL,
        data={
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise YouTubeIntegrationError("YouTube returned an incomplete credential response.")
    account.encrypted_access_token = encrypt_token(access_token)
    account.token_expires_at = timezone.now() + timedelta(
        seconds=int(token_data.get("expires_in", 0))
    )
    account.token_validated_at = timezone.now()
    account.refreshed_at = timezone.now()
    account.status = account.Status.CONNECTED
    account.save(
        update_fields=(
            "encrypted_access_token",
            "token_expires_at",
            "token_validated_at",
            "refreshed_at",
            "status",
        )
    )
    return access_token


def get_valid_youtube_token(account):
    token = decrypt_token(account.encrypted_access_token)
    if not token:
        raise YouTubeIntegrationError("Reconnect YouTube to restore access.", status=401)
    if account.token_expires_at and account.token_expires_at > timezone.now() + timedelta(minutes=2):
        return token
    return refresh_youtube_token(account)


def _youtube_api(url, token, params):
    return _json_request(
        f"{url}?{urlencode(params)}",
        headers={"Authorization": f"Bearer {token}"},
    )


def _youtube_duration_seconds(value):
    total = 0
    number = ""
    for character in (value or "").removeprefix("PT"):
        if character.isdigit():
            number += character
        elif number and character in "HMS":
            total += int(number) * {"H": 3600, "M": 60, "S": 1}[character]
            number = ""
    return total or None


def refresh_youtube_media(account):
    from .models import StreamingMedia

    token = get_valid_youtube_token(account)
    channel_response = _youtube_api(
        YOUTUBE_CHANNELS_URL,
        token,
        {"part": "contentDetails", "id": account.channel_identity, "maxResults": 1},
    )
    channels = channel_response.get("items") or []
    uploads_id = (
        channels[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if channels
        else None
    )
    if not uploads_id:
        raise YouTubeIntegrationError("YouTube could not find this channel's video list.")

    playlist_response = _youtube_api(
        YOUTUBE_PLAYLIST_ITEMS_URL,
        token,
        {
            "part": "contentDetails",
            "playlistId": uploads_id,
            "maxResults": 20,
        },
    )
    video_ids = [
        item.get("contentDetails", {}).get("videoId")
        for item in playlist_response.get("items") or []
    ]
    video_ids = [value for value in video_ids if value]
    if not video_ids:
        return 0, 0

    response = _youtube_api(
        YOUTUBE_VIDEOS_URL,
        token,
        {
            "part": "snippet,contentDetails,liveStreamingDetails,status",
            "id": ",".join(video_ids),
            "maxResults": 20,
        },
    )
    videos = [
        item for item in response.get("items") or []
        if item.get("status", {}).get("privacyStatus") in {"public", "unlisted"}
    ]
    for item in videos:
        snippet = item.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = thumbnails.get("medium") or thumbnails.get("default") or {}
        StreamingMedia.objects.update_or_create(
            account=account,
            kind=StreamingMedia.Kind.VIDEO,
            provider_media_id=item["id"],
            defaults={
                "parent_media_id": "",
                "title": snippet.get("title", ""),
                "canonical_url": f"https://www.youtube.com/watch?v={item['id']}",
                "thumbnail_url": thumbnail.get("url", ""),
                "published_at": _parse_youtube_datetime(snippet.get("publishedAt")),
                "duration_seconds": _youtube_duration_seconds(
                    item.get("contentDetails", {}).get("duration")
                ),
                "metadata_snapshot": item,
            },
        )
    return len(videos), 0


def _parse_youtube_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def apply_youtube_credentials(account, token_data, identity, channel):
    account.provider_identity = identity["sub"]
    account.channel_identity = channel["id"]
    account.display_name = channel["snippet"]["title"]
    account.channel_url = f"https://www.youtube.com/channel/{channel['id']}"
    account.granted_scopes = str(token_data.get("scope", "")).split()
    account.provider_metadata = {
        "google_identity": {
            "sub": identity["sub"],
            "email": identity.get("email", ""),
        },
        "channel": channel,
    }
    account.encrypted_access_token = encrypt_token(token_data["access_token"])
    refresh_token = token_data.get("refresh_token")
    if refresh_token:
        account.encrypted_refresh_token = encrypt_token(refresh_token)
    account.token_expires_at = timezone.now() + timedelta(
        seconds=int(token_data.get("expires_in", 0))
    )
    account.token_validated_at = timezone.now()
    account.refreshed_at = timezone.now()
    account.status = account.Status.CONNECTED
    account.save()


def revoke_youtube_account(account):
    token = decrypt_token(
        account.encrypted_refresh_token or account.encrypted_access_token
    )
    if token and youtube_is_configured():
        try:
            _json_request(YOUTUBE_REVOKE_URL, data={"token": token})
        except YouTubeIntegrationError:
            pass
