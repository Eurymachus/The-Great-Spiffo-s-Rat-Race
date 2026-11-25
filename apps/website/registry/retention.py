"""Conservative account deletion and retryable file cleanup.

Evidence-bearing history needs a reviewed redaction path. Never detach its owner
and describe it as anonymous merely because the login row has disappeared.
"""
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AccountClosureRecord, Participant, RetentionFileDeletion


class AccountDeletionBlocked(ValidationError):
    pass


# These records contain account-local data and are deliberately deleted with it.
ACCOUNT_LOCAL_MODELS = {
    "registry.notification", "registry.streamingaccount",
    "registry.runviewpreference", "registry.runworkspacepreference",
    "registry.participantviewpreference", "registry.participantworkspacepreference",
    "registry.workshopmodviewpreference", "registry.workshopmodworkspacepreference",
    "registry.legacyviewpreference", "registry.legacyworkspacepreference",
}
SAVED_VIEW_MODELS = {
    "registry.runsavedview", "registry.participantsavedview",
    "registry.workshopmodsavedview", "registry.legacysavedview",
}


def deletion_blockers(participant, *, reviewed_history=False):
    from .closure_redaction import REVIEWABLE_RELATIONS

    reasons = []
    if participant.is_staff or participant.is_superuser:
        reasons.append("Staff access must be removed before account deletion.")
    if participant.retention_hold:
        reasons.append("An active retention hold prevents deletion.")
    for relation in Participant._meta.related_objects:
        if relation.many_to_many:
            continue
        model = relation.related_model
        label = model._meta.label_lower
        if reviewed_history and (label, relation.field.name) in REVIEWABLE_RELATIONS:
            continue
        if label in ACCOUNT_LOCAL_MODELS:
            continue
        records = model._default_manager.using(participant._state.db).filter(
            **{relation.field.name: participant.pk}
        )
        if label in SAVED_VIEW_MODELS:
            records = records.filter(shared=True)
        if records.exists():
            reasons.append(f"Related {model._meta.verbose_name_plural} require a retention review.")
    return list(dict.fromkeys(reasons))


def ensure_account_deletable(participant):
    reasons = deletion_blockers(participant)
    if reasons:
        raise AccountDeletionBlocked(reasons)


def prepare_account_deletion(participant, using):
    """Called by pre_delete, including QuerySet.delete and cascade paths."""
    locked = Participant.objects.using(using).select_for_update().get(pk=participant.pk)
    ensure_account_deletable(locked)
    for relation in Participant._meta.related_objects:
        if relation.related_model._meta.label_lower in SAVED_VIEW_MODELS:
            relation.related_model.objects.using(using).filter(owner=locked, shared=False).delete()
    for kind, name in (("avatar", locked.avatar.name), ("quarantine", locked.avatar_review_path)):
        if name:
            RetentionFileDeletion.objects.using(using).get_or_create(kind=kind, name=name)


@transaction.atomic
def close_account(participant_id, *, redaction_token=None):
    from .closure_redaction import apply_redaction, build_redaction_plan, validate_review

    participant = Participant.objects.select_for_update().get(pk=participant_id)
    if not participant.deletion_requested_at:
        raise AccountDeletionBlocked("There is no pending closure request.")
    blockers = deletion_blockers(participant, reviewed_history=True)
    if blockers:
        raise AccountDeletionBlocked(blockers)
    plan = build_redaction_plan(participant, lock=True)
    if plan["has_history"]:
        if not redaction_token:
            raise AccountDeletionBlocked("Review the related history before confirming redaction.")
        validate_review(participant, plan, redaction_token)
    apply_redaction(participant, plan)
    ensure_account_deletable(participant)
    reference = participant.deletion_request_reference or uuid.uuid4()
    AccountClosureRecord.objects.get_or_create(
        reference=reference, defaults={"requested_at": participant.deletion_requested_at},
    )
    participant.delete()
    return reference


def overdue_registrations(now=None):
    return Participant.objects.filter(
        registered_at__lte=(now or timezone.now()) - timedelta(days=30),
        verified_at__isnull=True,
        status__in=(Participant.Status.PENDING, Participant.Status.EXPIRED),
        is_staff=False, is_superuser=False,
    )


def delete_overdue_registration(participant_id, now=None):
    with transaction.atomic():
        participant = overdue_registrations(now).select_for_update().filter(pk=participant_id).first()
        if participant is None:
            return False
        participant.delete()
        return True


def drain_file_deletions():
    """Keep failed jobs for retry; never remove a file from a rolled-back closure."""
    deleted = failed = 0
    for job in RetentionFileDeletion.objects.order_by("pk").iterator():
        try:
            if job.kind == "avatar":
                if Participant.objects.filter(avatar=job.name).exists():
                    raise ValueError("File is still referenced")
                path = Path(job.name)
                if path.is_absolute() or ".." in path.parts or not job.name.startswith("participant_avatars/"):
                    raise ValueError("Invalid avatar path")
                Participant._meta.get_field("avatar").storage.delete(job.name)
            elif job.kind == "quarantine":
                if Participant.objects.filter(avatar_review_path=job.name).exists():
                    raise ValueError("File is still referenced")
                root = Path(settings.AVATAR_QUARANTINE_ROOT).resolve()
                path = (root / job.name).resolve()
                if path == root or not path.is_relative_to(root):
                    raise ValueError("Invalid quarantine path")
                path.unlink(missing_ok=True)
            else:
                raise ValueError("Unknown file kind")
        except (OSError, ValueError):
            failed += 1
            continue
        job.delete()
        deleted += 1
    return deleted, failed
