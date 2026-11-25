"""Explicitly scoped first-release records for the participant download."""
from .models import LegacyRun, LegacyRunClaim, LegacyRunSubmission, WorkshopMod, WorkshopModVote


RESULT_FIELDS = (
    "id", "run_id", "status", "source", "source_rank", "character_name",
    "zombie_kills", "survival_days", "outposts_cleared", "maxed_skills",
    "challenge_progress", "survival_time_full", "reports_death", "submitted_at", "reviewed_at",
)
PERSONAL_SUBMISSION_FIELDS = RESULT_FIELDS + (
    "survival_time_input", "evidence_provider", "evidence_media_type",
    "evidence_media_id", "evidence_url", "evidence_title", "evidence_start_seconds", "evidence_end_seconds",
)


def first_release_data(participant):
    runs = []
    for run in LegacyRun.objects.filter(claimed_participant=participant).select_related("current_submission", "best_submission").order_by("pk"):
        runs.append({
            "id": run.pk, "historical_name": run.legacy_participant_name,
            "lifecycle": run.lifecycle, "character_name": run.character_name,
            "created_at": run.created_at, "updated_at": run.updated_at,
            "current_result": result_data(run.current_submission),
            "best_result": result_data(run.best_submission),
        })
    return {
        "workshop_requests": list(WorkshopMod.objects.filter(submitted_by=participant).order_by("pk").values(
            "id", "workshop_id", "title", "steam_url", "ruling", "is_recommended",
            "submission_reason", "public_rationale", "created_at", "updated_at", "reviewed_at",
        )),
        "workshop_votes": list(WorkshopModVote.objects.filter(voter=participant).order_by("pk").values(
            "id", "workshop_mod_id", "voter_name", "decision", "reason", "created_at", "updated_at",
        )),
        "rr1_runs": runs,
        "rr1_claims": [with_public_decision(row) for row in LegacyRunClaim.objects.filter(participant=participant).order_by("pk").values(
            "id", "run_id", "status", "evidence", "submitted_at", "reviewed_at", "review_note",
        )],
        "rr1_submissions": [with_public_decision(row) for row in LegacyRunSubmission.objects.filter(submitted_by=participant).order_by("pk").values(*PERSONAL_SUBMISSION_FIELDS, "review_note")],
    }


def with_public_decision(record):
    # Decline reasons are already delivered to participants; other review notes
    # are staff records and need separate review before disclosure.
    if record["status"] != "declined":
        record.pop("review_note", None)
    return record


def result_data(submission):
    if submission is None:
        return None
    # Linked imported/current results do not grant access to another submitter's
    # evidence, review notes, reviewer identity or the shared source spreadsheet.
    return {field: getattr(submission, field) for field in RESULT_FIELDS}
