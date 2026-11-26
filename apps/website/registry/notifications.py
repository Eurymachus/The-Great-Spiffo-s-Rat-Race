from django.urls import reverse
from .models import Notification, WorkshopMod


def notify_mod_ruling(mod):
    """Notify the submitter of a final ruling; full reasons remain in the catalogue."""
    if not mod.submitted_by_id or mod.ruling not in {
        WorkshopMod.Ruling.ALLOWED, WorkshopMod.Ruling.DISALLOWED,
    }:
        return None
    title = f"Mod {mod.get_ruling_display().lower()}: {mod.title}"
    reason = mod.public_rationale.strip() or "View the mod catalogue for the current ruling."
    return notify(
        mod.submitted_by,
        title=title if len(title) <= 120 else title[:117] + "...",
        message=reason if len(reason) <= 300 else reason[:270] + "... Full reason in catalogue.",
        category=Notification.Category.SUBMISSION,
        destination=reverse("registry:mods"),
    )


def notify(recipient, *, title, message, category=Notification.Category.ACCOUNT, destination=""):
    """Create durable participant feedback from account and workflow events."""
    return Notification.objects.create(
        recipient=recipient,
        category=category,
        title=title,
        message=message,
        destination=destination,
    )
