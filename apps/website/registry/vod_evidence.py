"""Provider-specific evidence checks. Never fetch a participant-supplied URL."""
import re
from copy import copy
from datetime import timedelta
from urllib.parse import urlsplit, parse_qs, urlencode

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import StreamingAccount


def parse_vod_url(value):
    try:
        url = urlsplit(value.strip())
        if url.scheme != "https" or url.username or url.password or url.port not in (None, 443):
            return None
    except ValueError:
        return None
    host = (url.hostname or "").lower()
    if host in {"twitch.tv", "www.twitch.tv", "m.twitch.tv"}:
        match = re.fullmatch(r"/videos/([0-9]+)/?", url.path)
        if match:
            return "twitch", match[1]
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        ids = parse_qs(url.query).get("v", []) if url.path == "/watch" else []
        match = re.fullmatch(r"/live/([A-Za-z0-9_-]{11})/?", url.path)
        media_id = ids[0] if len(ids) == 1 else (match[1] if match else "")
    elif host == "youtu.be":
        media_id = url.path.strip("/")
    else:
        return None
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", media_id):
        return "youtube", media_id
    return None


def _check_one_vod(submission):
    parsed = parse_vod_url(submission.evidence_url)
    if not parsed:
        return {"state": "missing", "reason": "No URL or VOD provided" if not submission.evidence_url else "VOD link invalid or unavailable"}
    provider, media_id = parsed
    account = StreamingAccount.objects.filter(
        participant_id=submission.submitter_id, provider=provider,
        status=StreamingAccount.Status.CONNECTED,
    ).first()
    result = {"provider": provider, "media_id": media_id}
    if not account:
        return {**result, "state": "uncertain", "reason": "A moderator must verify this video; no connected provider account is available."}
    from .streaming import TwitchIntegrationError, get_valid_twitch_token, _twitch_api, TWITCH_VIDEOS_URL
    from .youtube_integration import YouTubeIntegrationError, get_valid_youtube_token, _youtube_api, YOUTUBE_VIDEOS_URL
    from django.core.exceptions import ImproperlyConfigured
    try:
        if provider == "twitch":
            videos = _twitch_api(TWITCH_VIDEOS_URL, get_valid_twitch_token(account), {"id": media_id})
            item = videos[0] if videos else None
            if item:
                owned = item.get("user_id") == account.channel_identity
                published = item.get("created_at")
                finished = item.get("type") == "archive"
        else:
            videos = _youtube_api(YOUTUBE_VIDEOS_URL, get_valid_youtube_token(account),
                {"id": media_id, "part": "snippet,status,liveStreamingDetails"}).get("items", [])
            item = videos[0] if videos else None
            if item:
                owned = item.get("snippet", {}).get("channelId") == account.channel_identity
                published = item.get("liveStreamingDetails", {}).get("actualStartTime") or item.get("snippet", {}).get("publishedAt")
                finished = (item.get("status", {}).get("privacyStatus") in {"public", "unlisted"}
                    and item.get("snippet", {}).get("liveBroadcastContent") not in {"live", "upcoming"})
    except (TwitchIntegrationError, YouTubeIntegrationError, ImproperlyConfigured):
        return {**result, "state": "uncertain", "reason": "Provider verification is unavailable. A moderator must check the VOD."}
    if not item:
        return {**result, "state": "missing", "reason": "VOD link invalid or unavailable"}
    result.update(published_at=published)
    if not owned or not finished:
        return {**result, "state": "uncertain", "reason": "Review the video's channel ownership or availability as a completed VOD."}
    # Reusing a video must identify a fresh interval rather than silently covering new gameplay.
    previous = submission.run.submissions.filter(status="approved").exclude(pk=submission.pk)
    for earlier in previous.only("evidence_url", "evidence_end_seconds", "evidence_clips"):
        if any(parse_vod_url(clip.get("url", "")) == parsed
               for clip in earlier.evidence_clips if clip.get("kind") == "video"):
            return {**result, "state": "uncertain", "reason": "This broadcast was used before without a bounded interval. Review the new gameplay coverage."}
        if parse_vod_url(earlier.evidence_url) == parsed and (
            submission.evidence_start_seconds is None or earlier.evidence_end_seconds is None
            or submission.evidence_start_seconds < earlier.evidence_end_seconds
        ):
            return {**result, "state": "uncertain", "reason": "This VOD was used before. Review the new gameplay interval."}
    return {**result, "state": "valid", "reason": "Provider confirmed an accessible video on the participant's channel; gameplay remains auditable."}


def check_vod(submission):
    primary = _check_one_vod(submission)
    checks = [primary]
    for item in submission.evidence_clips:
        if item.get("kind") != "video":
            continue
        extra = copy(submission)
        extra.evidence_url = item["url"]
        extra.evidence_start_seconds = None
        extra.evidence_end_seconds = None
        checks.append(_check_one_vod(extra))
    worst = max(checks, key=lambda result: {"valid":0, "uncertain":1, "missing":2}[result["state"]])
    dates = [result["published_at"] for result in checks if result.get("published_at")]
    return {**primary, "state":worst["state"], "reason":worst["reason"],
        "published_at":min(dates) if dates else None, "videos":checks}


def evidence_presentation(submission, host):
    parsed = parse_vod_url(submission.evidence_url)
    embed = ""
    if parsed:
        provider, media_id = parsed
        start = submission.evidence_start_seconds or 0
        if provider == "youtube":
            embed = f"https://www.youtube-nocookie.com/embed/{media_id}?" + urlencode({"start": start})
        else:
            embed = "https://player.twitch.tv/?" + urlencode({"video": media_id, "parent": host, "autoplay": "false", "time": f"{start}s"})
    published = parse_datetime(submission.evidence_check.get("published_at") or "")
    if published and timezone.is_naive(published):
        published = timezone.make_aware(published)
    deadline = published + timedelta(days=7) if published else None
    return {"embed": embed, "deadline": deadline,
        "expired": bool(deadline and deadline <= timezone.now()),
        "reason": submission.evidence_check.get("reason", "Evidence has not been checked under the new policy.")}


def current_evidence_finding(submission):
    if not submission.evidence_url:
        return "No URL or VOD provided"
    if not parse_vod_url(submission.evidence_url) or submission.evidence_check.get("state") == "missing":
        return "VOD link invalid or unavailable"
    return ""
