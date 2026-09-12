from django.core.exceptions import ObjectDoesNotExist

from registry.models import ChallengeRun, RunSubmission, SubmissionAuditEntry
from registry.run_block_cache import decode_run_export_cached
from registry.run_exports import InvalidRunExport


AUTHORITY_ACCESSORS = (
    "contract_state",
    "character_record",
    "starting_location",
    "authoritative_outposts",
    "authoritative_skills",
    "authoritative_landmarks",
    "kill_summary",
    "weapon_kills",
    "daily_records",
    "statistic_summaries",
)


def _stored_character_name(projection):
    if not isinstance(projection, dict):
        return ""
    character = projection.get("character")
    if not isinstance(character, dict):
        return ""
    for snapshot_name in ("current", "starting"):
        snapshot = character.get(snapshot_name)
        if isinstance(snapshot, dict) and snapshot.get("displayName"):
            return str(snapshot["displayName"])
    return str(character.get("displayName") or "")


def reset_run_moderation(run_ids):
    runs = list(
        ChallengeRun.objects.select_for_update()
        .filter(pk__in=run_ids)
        .order_by("first_submitted_at", "pk")
    )
    submissions = list(
        RunSubmission.objects.select_for_update()
        .filter(run__in=runs)
        .order_by("run_id", "-submitted_at", "-pk")
    )

    latest_by_run = {}
    for submission in submissions:
        latest_by_run.setdefault(submission.run_id, submission)

    RunSubmission.objects.filter(run__in=runs).update(
        status=RunSubmission.Status.RECEIVED,
        reviewed_at=None,
        reviewed_by=None,
        review_note="",
        evidence_requested_at=None,
        evidence_requested_by=None,
        evidence_request_note="",
        baseline_submission=None,
        approval_method="",
        approval_policy_version=0,
        routing_reasons=[],
        evidence_check={},
        evidence_checked_at=None,
    )
    SubmissionAuditEntry.objects.filter(submission__run__in=runs).delete()

    authority_records = 0
    for run in runs:
        for accessor in AUTHORITY_ACCESSORS:
            try:
                relation = getattr(run, accessor)
            except ObjectDoesNotExist:
                continue
            if hasattr(relation, "all"):
                deleted, _ = relation.all().delete()
            else:
                deleted, _ = relation.delete()
            authority_records += deleted

        latest = latest_by_run.get(run.pk)
        run.status = ChallengeRun.Status.PENDING
        run.approved_submission = None
        if latest:
            run.challenge_mode = latest.challenge_mode
            run.challenge_id = latest.challenge_id
            run.challenge_game_mode = latest.challenge_game_mode
            run.export_format = latest.export_format
            run.generated_at = latest.generated_at
            run.current_kills = latest.current_kills
            run.event_sequence = latest.event_sequence
            run.event_hash = latest.event_hash
            run.latest_projection = latest.projection
            run.reported_lifecycle_status = latest.reported_lifecycle_status
            try:
                decoded = decode_run_export_cached(latest.raw_export)
            except InvalidRunExport:
                # Historical test exports can become invalid as validation evolves.
                # A moderation reset must preserve them and clear derived authority,
                # rather than requiring the original upload to validate again.
                run.character_name = _stored_character_name(latest.projection)
                run.bootstrapped = False
                run.latest_events = []
            else:
                run.character_name = decoded.character_name
                run.bootstrapped = decoded.bootstrapped
                run.latest_events = decoded.events
        run.lifecycle_status = run.lifecycle_status if run.lifecycle_status in (ChallengeRun.Lifecycle.ABANDONED, ChallengeRun.Lifecycle.INVALIDATED) else (
            ChallengeRun.Lifecycle.ABANDONED
            if run.participant_deactivated_at
            else ChallengeRun.Lifecycle.ACTIVE
        )
        run.save()

    return {
        "runs": len(runs),
        "submissions": len(submissions),
        "authority_records": authority_records,
    }
