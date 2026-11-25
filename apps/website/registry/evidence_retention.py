"""Scheduled expiry of first-release moderation text; results are retained."""
from django.db import transaction
from django.utils import timezone

from .closure_redaction import _import_changes
from .legacy_imports import normalise_legacy_name
from .models import LegacyDataImport, LegacyRun, LegacyRunClaim, LegacyRunSubmission, Participant, WorkshopMod, WorkshopModVote


def two_year_cutoff(now):
    try:
        return now.replace(year=now.year - 2)
    except ValueError:
        return now.replace(year=now.year - 2, day=28)


def _identities(rows, fields):
    return {row[field] for row in rows for field in fields if row.get(field)}


def _held(identities):
    # Stable ordering and no joined locks, matching the account-before-record
    # ordering of interactive review and closure.
    accounts = list(Participant.objects.select_for_update().filter(pk__in=identities).order_by("pk"))
    return any(account.retention_hold for account in accounts)


def _latest(rows, fields, fallback):
    return max([fallback] + [row[field] for row in rows for field in fields if row.get(field)])


@transaction.atomic
def retire_run_evidence(run_id, *, apply=False, now=None):
    now = now or timezone.now()
    cutoff = two_year_cutoff(now)
    run = LegacyRun.objects.get(pk=run_id)
    if run.lifecycle == LegacyRun.Lifecycle.ACTIVE or run.updated_at > cutoff:
        return "retained"
    submissions = list(LegacyRunSubmission.objects.filter(run=run).values())
    claims = list(LegacyRunClaim.objects.filter(run=run).values())
    imports = list(LegacyDataImport.objects.all().values())
    identities = _identities(submissions, ("submitted_by_id", "reviewed_by_id")) | _identities(claims, ("participant_id", "reviewed_by_id"))
    if run.claimed_participant_id:
        identities.add(run.claimed_participant_id)
    names = {normalise_legacy_name(run.legacy_participant_name)} if not run.identity_removed else set()
    changes = {row["id"]: change for row in imports if names and (change := _import_changes(row, names))}
    affected_imports = [row for row in imports if row["id"] in changes]
    identities |= _identities(affected_imports, ("uploaded_by_id",))
    if _held(identities):
        return "held"
    run = LegacyRun.objects.select_for_update().get(pk=run_id)
    current_submissions = list(LegacyRunSubmission.objects.select_for_update().filter(run=run).order_by("pk").values())
    current_claims = list(LegacyRunClaim.objects.select_for_update().filter(run=run).order_by("pk").values())
    if sorted(submissions, key=lambda row: row["id"]) != current_submissions or sorted(claims, key=lambda row: row["id"]) != current_claims:
        return "changed"
    if run.claimed_participant_id and run.claimed_participant_id not in identities:
        return "changed"
    if run.lifecycle == LegacyRun.Lifecycle.ACTIVE or run.updated_at > cutoff:
        return "retained"
    if any(row["status"] == "received" or row["reviewed_at"] is None for row in submissions):
        return "retained"
    if any(row["status"] == "pending" or row["reviewed_at"] is None for row in claims):
        return "retained"
    if _latest(submissions + claims, ("submitted_at", "reviewed_at"), run.updated_at) > cutoff:
        return "retained"
    # Recent or unresolved source reviews remain evidence; do not silently
    # rewrite their inputs. Recheck locked snapshots against the plan.
    for original in affected_imports:
        current = LegacyDataImport.objects.select_for_update().values().get(pk=original["id"])
        if current != original:
            return "changed"
        if current["status"] == "preview" or _latest([current], ("uploaded_at", "imported_at"), run.updated_at) > cutoff:
            return "retained"
    text_fields = ("review_note", "evidence_provider", "evidence_media_type", "evidence_media_id", "evidence_url", "evidence_title")
    has_text = any(any(row[field] for field in text_fields) or row["evidence_start_seconds"] is not None or row["evidence_end_seconds"] is not None for row in submissions)
    has_text = has_text or any(row["evidence"] or row["review_note"] for row in claims) or bool(changes)
    if not has_text:
        return "empty"
    if apply:
        LegacyRunSubmission.objects.filter(run=run).update(**dict.fromkeys(text_fields, ""), evidence_start_seconds=None, evidence_end_seconds=None)
        LegacyRunClaim.objects.filter(run=run).update(evidence="", review_note="")
        for pk, change in changes.items():
            LegacyDataImport.objects.filter(pk=pk).update(**change, redacted_at=now)
    return "eligible"


@transaction.atomic
def retire_workshop_notes(mod_id, *, apply=False, now=None):
    cutoff = two_year_cutoff(now or timezone.now())
    mod = WorkshopMod.objects.get(pk=mod_id)
    votes = list(WorkshopModVote.objects.filter(workshop_mod=mod).order_by("pk").values())
    identities = {pk for pk in (mod.submitted_by_id, mod.reviewed_by_id) if pk} | _identities(votes, ("voter_id",))
    if _held(identities):
        return "held"
    mod = WorkshopMod.objects.select_for_update().get(pk=mod_id)
    current_votes = list(WorkshopModVote.objects.select_for_update().filter(workshop_mod=mod).order_by("pk").values())
    if votes != current_votes or any(pk and pk not in identities for pk in (mod.submitted_by_id, mod.reviewed_by_id)):
        return "changed"
    if mod.ruling == WorkshopMod.Ruling.PENDING or mod.reviewed_at is None:
        return "retained"
    anchor = max(mod.created_at, mod.updated_at, mod.reviewed_at)
    if _latest(votes, ("created_at", "updated_at"), anchor) > cutoff:
        return "retained"
    if not (mod.submission_reason or mod.unstable_ruling_notes or any(row["reason"] for row in votes)):
        return "empty"
    if apply:
        WorkshopMod.objects.filter(pk=mod.pk).update(submission_reason="", unstable_ruling_notes="")
        WorkshopModVote.objects.filter(workshop_mod=mod).update(reason="")
    return "eligible"
