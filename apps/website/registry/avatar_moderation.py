import base64
import io
import json
import uuid
from pathlib import Path
from urllib import error, request

from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import Participant


class InvalidAvatar(ValueError):
    pass


def prepare_avatar(upload):
    try:
        upload.seek(0)
        with Image.open(upload) as source:
            source.load()
            if source.width < 80 or source.height < 80:
                raise InvalidAvatar("The avatar must be at least 80 × 80 pixels.")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image = ImageOps.fit(image, (512, 512), method=Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidAvatar("The uploaded file could not be read as a safe image.") from exc
    output = io.BytesIO()
    image.save(output, format="WEBP", quality=88, method=6)
    return output.getvalue()


def moderate_avatar(image_bytes):
    if not settings.OPENAI_API_KEY:
        return "pending", "Automatic moderation is not configured."
    payload = json.dumps({
        "model": "omni-moderation-latest",
        "input": [{
            "type": "image_url",
            "image_url": {"url": "data:image/webp;base64," + base64.b64encode(image_bytes).decode("ascii")},
        }],
    }).encode("utf-8")
    api_request = request.Request(
        settings.OPENAI_MODERATION_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(api_request, timeout=15) as response:
            result = json.load(response)["results"][0]
    except (error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        return "pending", "Automatic moderation was unavailable."
    if result.get("flagged"):
        categories = result.get("categories", {})
        flagged = [name for name, present in categories.items() if present]
        return "rejected", "Flagged by automatic moderation" + (": " + ", ".join(flagged) if flagged else ".")
    return "approved", "Passed automatic moderation."


def submit_avatar(participant, upload):
    image_bytes = prepare_avatar(upload)
    outcome, note = moderate_avatar(image_bytes)
    if participant.avatar_review_path:
        (Path(settings.AVATAR_QUARANTINE_ROOT) / participant.avatar_review_path).unlink(missing_ok=True)
    participant.avatar_submitted_at = timezone.now()
    participant.avatar_moderation_note = note
    participant.avatar_review_path = ""
    if outcome == "approved":
        if participant.avatar:
            participant.avatar.delete(save=False)
        participant.avatar.save(f"{uuid.uuid4().hex}.webp", ContentFile(image_bytes), save=False)
        participant.avatar_status = Participant.AvatarStatus.APPROVED
    elif outcome == "pending":
        quarantine_root = Path(settings.AVATAR_QUARANTINE_ROOT)
        quarantine_root.mkdir(parents=True, exist_ok=True)
        filename = f"{participant.pk}-{uuid.uuid4().hex}.webp"
        (quarantine_root / filename).write_bytes(image_bytes)
        participant.avatar_review_path = filename
        participant.avatar_status = Participant.AvatarStatus.PENDING
    else:
        participant.avatar_status = Participant.AvatarStatus.REJECTED
    participant.save(update_fields=(
        "avatar", "avatar_status", "avatar_review_path",
        "avatar_moderation_note", "avatar_submitted_at",
    ))
    return outcome


def approve_pending_avatar(participant):
    if not participant.avatar_review_path:
        return False
    path = Path(settings.AVATAR_QUARANTINE_ROOT) / participant.avatar_review_path
    if not path.is_file():
        return False
    if participant.avatar:
        participant.avatar.delete(save=False)
    participant.avatar.save(f"{uuid.uuid4().hex}.webp", ContentFile(path.read_bytes()), save=False)
    path.unlink(missing_ok=True)
    participant.avatar_status = Participant.AvatarStatus.APPROVED
    participant.avatar_review_path = ""
    participant.avatar_moderation_note = "Approved by an administrator."
    participant.save(update_fields=("avatar", "avatar_status", "avatar_review_path", "avatar_moderation_note"))
    return True


def reject_pending_avatar(participant):
    if participant.avatar_review_path:
        (Path(settings.AVATAR_QUARANTINE_ROOT) / participant.avatar_review_path).unlink(missing_ok=True)
    participant.avatar_status = Participant.AvatarStatus.REJECTED
    participant.avatar_review_path = ""
    participant.avatar_moderation_note = "Rejected by an administrator."
    participant.save(update_fields=("avatar_status", "avatar_review_path", "avatar_moderation_note"))


def remove_avatar(participant):
    if participant.avatar:
        participant.avatar.delete(save=False)
    if participant.avatar_review_path:
        (Path(settings.AVATAR_QUARANTINE_ROOT) / participant.avatar_review_path).unlink(missing_ok=True)
    participant.avatar = ""
    participant.avatar_status = Participant.AvatarStatus.NONE
    participant.avatar_review_path = ""
    participant.avatar_moderation_note = ""
    participant.avatar_submitted_at = None
    participant.save(update_fields=(
        "avatar", "avatar_status", "avatar_review_path",
        "avatar_moderation_note", "avatar_submitted_at",
    ))
