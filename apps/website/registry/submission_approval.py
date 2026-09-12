from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import ChallengeRun, Participant, ParticipantChallengeModeLimit, RunSubmission, Notification
from .run_block_cache import attach_verified_blocks, decode_run_export_cached
from .run_authority import refresh_initial_run_authority
from .challenge_modes import resolve_challenge_mode
from .notifications import notify

POLICY_VERSION = 3

class ApprovalBlocked(Exception):
    def __init__(self, message, *, related_run=None):
        super().__init__(message)
        self.related_run = related_run


@transaction.atomic
def approve_submission(submission_id, reviewer=None, *, automatic=False):
    submission = RunSubmission.objects.select_related('run').get(pk=submission_id)
    if submission.run.participant_id:
        Participant.objects.select_for_update().get(pk=submission.run.participant_id)
    run = ChallengeRun.objects.select_for_update().get(pk=submission.run_id)
    submission = RunSubmission.objects.select_for_update().get(pk=submission_id)
    submission.run = run
    if run.lifecycle_status == ChallengeRun.Lifecycle.INVALIDATED:
        raise ApprovalBlocked(f'This run is {run.get_lifecycle_status_display().lower()} and cannot accept approvals.')
    from .vod_evidence import parse_vod_url
    if (not run.challenge_mode or run.challenge_mode.evidence_required) and (not parse_vod_url(submission.evidence_url) or submission.evidence_check.get('state') == 'missing'):
        raise ApprovalBlocked('Supply valid VOD evidence before approval.')
    from .run_review import build_run_review
    if build_run_review(submission)['severity'] == 'danger':
        raise ApprovalBlocked('Resolve the blocking integrity finding before approval.')
    if automatic:
        reasons = review_triggers(submission)
        if reasons:
            raise ApprovalBlocked('This submission requires human review.')
        if (not run.challenge_mode or run.challenge_mode.evidence_required) and (submission.evidence_check.get('state') != 'valid'
            or not submission.evidence_checked_at
            or submission.evidence_checked_at < timezone.now() - timedelta(minutes=15)
            or submission.evidence_check.get('baseline_id') != str(run.approved_submission_id)
            or submission.evidence_check.get('url') != submission.evidence_url
            or submission.evidence_check.get('start') != submission.evidence_start_seconds
            or submission.evidence_check.get('end') != submission.evidence_end_seconds
            or submission.evidence_check.get('clips') != submission.evidence_clips):
            raise ApprovalBlocked('This submission requires human review or evidence.')
    if submission.status != RunSubmission.Status.RECEIVED:
        raise ApprovalBlocked('This submission has already been reviewed.')
    oldest_pending = run.submissions.filter(status__in=RunSubmission.moderation_queue_statuses()).order_by('submitted_at', 'pk').first()
    if oldest_pending and oldest_pending.pk != submission.pk:
        raise ApprovalBlocked("Review the run's older pending submission first.")
    baseline = run.approved_submission
    starting_challenge_id = run.starting_challenge_id
    expected_challenge_id = baseline.challenge_id if baseline and baseline.challenge_id else starting_challenge_id
    if expected_challenge_id and submission.challenge_id and (expected_challenge_id != submission.challenge_id):
        raise ApprovalBlocked('This submission reports a different challenge mode from the approved baseline.')
    if baseline:
        if submission.event_sequence < baseline.event_sequence:
            raise ApprovalBlocked('This submission is older than the current approved snapshot.')
        if submission.event_sequence == baseline.event_sequence:
            if submission.event_hash != baseline.event_hash:
                raise ApprovalBlocked('This submission conflicts with the current approved ledger.')
            if submission.generated_at <= baseline.generated_at:
                raise ApprovalBlocked('This submission is not newer than the current approved snapshot.')
    approved_events = list(run.latest_events or [])
    if baseline and (not approved_events):
        approved_events = list(decode_run_export_cached(baseline.raw_export).events)
    decoded = decode_run_export_cached(submission.raw_export)
    if baseline and approved_events != list(decoded.events[:len(approved_events)]):
        raise ApprovalBlocked('This submission changes previously approved event history and cannot be approved.')
    if run.lifecycle_status != ChallengeRun.Lifecycle.ABANDONED and decoded.lifecycle == ChallengeRun.Lifecycle.ACTIVE and run.participant and run.challenge_mode:
        override = ParticipantChallengeModeLimit.objects.filter(participant=run.participant, challenge_mode=run.challenge_mode).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).first()
        active_limit = override.max_active_runs if override and override.max_active_runs is not None else run.challenge_mode.max_active_runs_per_participant
        approved_active = list(ChallengeRun.objects.select_for_update().filter(participant=run.participant, challenge_mode=run.challenge_mode, lifecycle_status=ChallengeRun.Lifecycle.ACTIVE, status=ChallengeRun.Status.OFFICIAL).exclude(pk=run.pk).order_by("pk"))
        unresolved_death = RunSubmission.objects.filter(submitter=run.participant, challenge_mode=run.challenge_mode, reported_lifecycle_status=ChallengeRun.Lifecycle.DECEASED, status__in=RunSubmission.moderation_queue_statuses(), submitted_at__lt=submission.submitted_at).exclude(run=run).select_related("run").order_by("submitted_at", "pk").first()
        if unresolved_death:
            raise ApprovalBlocked(
                f"Review the earlier death submission for {unresolved_death.run.character_name or 'Unnamed survivor'} before approving this active run.",
                related_run=unresolved_death.run,
            )
        if len(approved_active) >= active_limit:
            raise ApprovalBlocked(
                f"Active-run limit reached: this participant has {len(approved_active)} approved active runs in this challenge (limit: {active_limit}). Review their active runs before approving another.",
                related_run=approved_active[0] if approved_active else None,
            )
    if decoded.event_blocks and (not submission.event_blocks.exists()):
        attach_verified_blocks(submission, decoded)
    reviewed_at = timezone.now()
    submission.status = RunSubmission.Status.APPROVED
    submission.reviewed_at = reviewed_at
    submission.reviewed_by = reviewer
    submission.review_note = ''
    submission.baseline_submission = baseline
    submission.approval_method = 'automatic' if automatic else 'human'
    submission.approval_policy_version = POLICY_VERSION
    submission.save(update_fields=('status', 'reviewed_at', 'reviewed_by', 'review_note', 'baseline_submission', 'approval_method', 'approval_policy_version'))
    run.status = ChallengeRun.Status.OFFICIAL
    run.approved_submission = submission
    run.challenge_mode = resolve_challenge_mode(decoded.challenge_id, decoded.challenge_game_mode)
    run.challenge_id = decoded.challenge_id
    run.challenge_game_mode = decoded.challenge_game_mode
    run.export_format = decoded.format
    run.generated_at = decoded.generated_at
    run.current_kills = decoded.current_kills
    run.event_sequence = decoded.event_sequence
    run.event_hash = decoded.event_hash
    run.character_name = decoded.character_name
    run.bootstrapped = decoded.bootstrapped
    run.latest_projection = decoded.projection
    run.latest_events = decoded.events
    if run.lifecycle_status != ChallengeRun.Lifecycle.ABANDONED and decoded.lifecycle == ChallengeRun.Lifecycle.DECEASED:
        run.lifecycle_status = ChallengeRun.Lifecycle.DECEASED
    run.reported_lifecycle_status = decoded.lifecycle
    run.save()
    incremental = bool(baseline and baseline.event_sequence <= len(decoded.events) and (approved_events == decoded.events[:baseline.event_sequence]))
    refresh_initial_run_authority(run, decoded.projection, decoded.events, previous_event_sequence=baseline.event_sequence if incremental else 0)
    if run.participant:
        notify(run.participant, category=Notification.Category.SUBMISSION, title='Submission approved', message='Your Rat Race submission has been approved.', destination=reverse('registry:account'))
    return submission


def review_triggers(submission):
    """Compare only new evidence with the currently accepted baseline."""
    from .run_review import build_run_review
    baseline = submission.run.approved_submission
    if not baseline:
        return ["First approval for this run"]
    decoded = decode_run_export_cached(submission.raw_export)
    before = decode_run_export_cached(baseline.raw_export)
    reasons = [f["title"] for f in build_run_review(submission)["findings"]
               if f["level"] in {"warning", "danger"}
               and f["title"] != "Run began with a partial day"]
    if decoded.bootstrapped and not before.bootstrapped:
        reasons.append("New partial tracking history")
    labels = {"run.debug.enabled": "Debug used", "outpost.completed": "Outpost completed",
              "run.clock.repaired": "Game-time correction recorded"}
    for event in decoded.events[len(before.events):]:
        kind = event.get("event_type", "")
        payload = event.get("payload") or {}
        if kind in labels:
            reasons.append(labels[kind])
        elif any(term in kind for term in ("clock", "reconcil", "recover", "time.deviation")):
            reasons.append("Time deviation or reconciliation recorded")
        if kind == "session.started" and any(payload.get(key) for key in
                ("addedMods", "removedMods", "changedMods", "addedWorkshopIds", "removedWorkshopIds")):
            reasons.append("Mods changed")
    for key in ("activeMods", "recovery", "challenge"):
        if decoded.projection.get(key) != before.projection.get(key):
            reasons.append(f"{key}: evidence changed")
    for key in ("starting", "chosenStartingRegion", "startingLocation", "selectedStartingTraits", "startingEffectiveTraits", "selectedStartingTraitsPartial"):
        if (decoded.projection.get("character") or {}).get(key) != (before.projection.get("character") or {}).get(key):
            reasons.append(f"Starting character evidence changed: {key}")
    # Whole-outpost repeat completions are projection evidence, not new ledger events.
    def completion_counts(projection):
        outposts = projection.get("outposts") or {}
        entries = outposts.get("entries", []) if isinstance(outposts, dict) else outposts
        if isinstance(entries, dict):
            entries = list(entries.values())
        return {str(item.get("id") or item.get("outpostId")): (item.get("lifecycle") or {}).get("completionCount", 0)
                for item in entries if isinstance(item, dict) and (item.get("lifecycle") or {}).get("completionCount", 0)}
    if completion_counts(decoded.projection) != completion_counts(before.projection):
        reasons.append("Outpost completion evidence changed")
    if decoded.lifecycle != before.lifecycle or decoded.lifecycle != ChallengeRun.Lifecycle.ACTIVE:
        reasons.append("Run ending or lifecycle change")
    if submission.current_kills < baseline.current_kills:
        reasons.append("Cumulative kills decreased")
    return list(dict.fromkeys(reasons))


def route_run(run_id):
    """Reassess the ordered queue, advancing only a clean eligible prefix."""
    if ChallengeRun.objects.filter(pk=run_id, lifecycle_status__in=("invalidated",)).exists():
        return
    from .vod_evidence import check_vod
    from .run_exports import InvalidRunExport
    for submission in RunSubmission.objects.filter(run_id=run_id,
            status__in=RunSubmission.moderation_queue_statuses()).order_by("submitted_at", "pk"):
        if submission.status == RunSubmission.Status.AWAITING_EVIDENCE:
            break
        evidence = check_vod(submission)
        evidence.update(baseline_id=str(submission.run.approved_submission_id),
            url=submission.evidence_url, start=submission.evidence_start_seconds,
            end=submission.evidence_end_seconds, clips=submission.evidence_clips)
        try:
            reasons = review_triggers(submission)
        except InvalidRunExport as exc:
            reasons = [str(exc)]
        if evidence["state"] != "valid" and (not submission.run.challenge_mode or submission.run.challenge_mode.evidence_required):
            reasons.append(evidence["reason"])
        with transaction.atomic():
            run = ChallengeRun.objects.select_for_update().get(pk=run_id)
            locked = RunSubmission.objects.select_for_update().get(pk=submission.pk)
            if (locked.status != RunSubmission.Status.RECEIVED
                or locked.evidence_url != submission.evidence_url
                or locked.evidence_start_seconds != submission.evidence_start_seconds
                or locked.evidence_end_seconds != submission.evidence_end_seconds
                or locked.evidence_clips != submission.evidence_clips
                or run.approved_submission_id != submission.run.approved_submission_id):
                break
            locked.evidence_check = evidence
            locked.evidence_checked_at = timezone.now()
            locked.routing_reasons = reasons
            if evidence["state"] == "missing" and (not run.challenge_mode or run.challenge_mode.evidence_required):
                locked.status = RunSubmission.Status.AWAITING_EVIDENCE
                locked.evidence_request_note = evidence["reason"]
                locked.evidence_requested_at = timezone.now()
                if locked.submitter_id:
                    notify(locked.submitter, category=Notification.Category.SUBMISSION,
                        title="Evidence needed", message=evidence["reason"],
                        destination=reverse("registry:update_run_submission_evidence", args=(locked.pk,)))
            locked.save(update_fields=("evidence_check", "evidence_checked_at", "routing_reasons",
                "status", "evidence_request_note", "evidence_requested_at"))
        if reasons:
            break
        try:
            approve_submission(submission.pk, automatic=True)
        except ApprovalBlocked as exc:
            RunSubmission.objects.filter(pk=submission.pk, status="received").update(routing_reasons=[str(exc)])
            break
