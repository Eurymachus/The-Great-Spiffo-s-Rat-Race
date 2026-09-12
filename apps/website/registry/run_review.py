import json
from collections import Counter
from datetime import datetime, timezone

from django.utils import timezone as django_timezone

from .models import RunSubmission
from .run_exports import InvalidRunExport
from .run_block_cache import decode_run_export_cached
from zomboid_catalogue.models import CatalogueEntry
from zomboid_catalogue.resolver import resolve_identifier


EVENT_LABELS = {
    "session.started": "Session started",
    "day.started": "New in-game day",
    "skill.level.reached": "Skill level reached",
    "outpost.deliverable.completed": "Outpost delivery completed",
}


def _event_time(event):
    try:
        return datetime.fromtimestamp(int(event.get("utc", 0)), tz=timezone.utc)
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def _event_day(event):
    try:
        return max(1, int(float(event.get("world_age_hours", 0)) // 24) + 1)
    except (TypeError, ValueError):
        return None


def _catalogue_name(kind, stable_id):
    if not stable_id:
        return None
    entry = resolve_identifier(kind, str(stable_id))
    return entry.display_name if entry else None


def _payload_summary(event):
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    event_type = event.get("event_type", "")
    if event_type == "session.started":
        character = payload.get("character")
        if isinstance(character, dict):
            name = character.get("displayName") or character.get("display_name")
            if name:
                return str(name)
        return "The run ledger begins."
    if event_type == "day.started":
        return "Partial/bootstrap day" if payload.get("partial") else "Complete day"
    if event_type == "skill.level.reached":
        skill_id = payload.get("skillId") or payload.get("skill")
        skill = (
            _catalogue_name(CatalogueEntry.Kind.SKILL, skill_id)
            or payload.get("skillName")
            or skill_id
            or "Skill"
        )
        level = payload.get("level")
        return f"{skill} reached level {level}" if level is not None else str(skill)
    if event_type == "outpost.deliverable.completed":
        outpost_id = payload.get("outpostId") or payload.get("outpost")
        deliverable_id = payload.get("deliverableId") or payload.get("deliverable")
        outpost = (
            _catalogue_name(CatalogueEntry.Kind.OUTPOST, outpost_id)
            or outpost_id
            or "Outpost"
        )
        deliverable = (
            _catalogue_name(CatalogueEntry.Kind.DELIVERABLE, deliverable_id)
            or deliverable_id
        )
        value = payload.get("value")
        parts = [str(outpost)]
        if deliverable:
            parts.append(str(deliverable))
        if value is not None:
            parts.append(f"value {value}")
        return " · ".join(parts)

    useful = []
    for key, value in payload.items():
        if isinstance(value, (str, int, float, bool)) and len(useful) < 3:
            useful.append(f"{key.replace('_', ' ')}: {value}")
    return " · ".join(useful) or "Recorded event"


def _event_identifiers(event):
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    event_type = event.get("event_type", "")
    if event_type == "skill.level.reached":
        stable_id = payload.get("skillId") or payload.get("skill")
        return f"Skill ID: {stable_id}" if stable_id else ""
    if event_type == "outpost.deliverable.completed":
        identifiers = []
        if payload.get("outpostId"):
            identifiers.append(f"Outpost ID: {payload['outpostId']}")
        if payload.get("deliverableId"):
            identifiers.append(f"Deliverable ID: {payload['deliverableId']}")
        return " · ".join(identifiers)
    return ""


def _event_rows(events, baseline_events=(), accepted=False):
    rows = []
    for index, event in enumerate(events):
        event_type = str(event.get("event_type") or "unknown")
        payload = event.get("payload") or {}
        reason = {"run.debug.enabled": "Debug used", "outpost.completed": "Outpost completed", "run.clock.repaired": "Game-time correction recorded"}.get(event_type, "")
        if not reason and any(term in event_type for term in ("clock", "reconcil", "recover", "time.deviation")):
            reason = "Time deviation or reconciliation recorded"
        if event_type == "session.started" and any(payload.get(key) for key in ("addedMods", "removedMods", "changedMods", "addedWorkshopIds", "removedWorkshopIds")):
            reason = "Mods changed"
        changed = index < len(baseline_events) and event != baseline_events[index]
        reviewed = accepted or (index < len(baseline_events) and not changed)
        level = "danger" if changed else ("info" if reviewed else "warning") if reason else ""
        if changed:
            reason = "Previously approved event changed"
        elif reason:
            reason += " (covered by approval)" if reviewed else " (human review required)"
        rows.append(
            {
                "sequence": event.get("sequence"),
                "review_level": level,
                "review_reason": reason,
                "label": EVENT_LABELS.get(
                    event_type, event_type.replace(".", " ").replace("_", " ").title()
                ),
                "event_type": event_type,
                "summary": _payload_summary(event),
                "identifiers": _event_identifiers(event),
                "day": _event_day(event),
                "occurred_at": _event_time(event),
            }
        )
    return rows


def _baseline_for(current_submission):
    if current_submission.status in (RunSubmission.Status.APPROVED, RunSubmission.Status.DECLINED):
        return current_submission.baseline_submission
    current_approved = current_submission.run.approved_submission
    if current_approved and current_approved.pk != current_submission.pk:
        return current_approved
    return current_submission.baseline_submission


def review_severity(findings):
    """Return the most serious actionable finding level."""
    levels = {"pass": 0, "warning": 1, "danger": 2}
    return max(
        (finding["level"] for finding in findings if finding["level"] in levels),
        key=levels.get,
        default="pass",
    )


def build_run_review(current_submission):
    run = current_submission.run
    try:
        decoded = decode_run_export_cached(current_submission.raw_export)
    except InvalidRunExport as exc:
        return {
            "current_submission": current_submission,
            "baseline": _baseline_for(current_submission),
            "comparison": None,
            "invalid_export": True,
            "severity": "danger",
            "findings": [{
                "level": "danger",
                "title": "Export could not be validated",
                "message": str(exc) + " Approval is blocked. The stored submission has been preserved.",
            }],
            "event_counts": [],
            "event_rows": [],
            "snapshot_json": json.dumps(current_submission.projection, indent=2, ensure_ascii=False),
            "event_history_json": "Unavailable: export validation failed.",
        }
    events = list(decoded.events)
    counts = Counter(str(event.get("event_type") or "unknown") for event in events)
    findings = [
        {
            "level": "pass",
            "title": "Export integrity verified",
            "message": "The envelope checksum and event-ledger hash were valid when this submission was received.",
        },
        {
            "level": "pass",
            "title": "Event sequence verified",
            "message": f"{len(events):,} ledger events decoded in sequence.",
        },
    ]
    if decoded.bootstrapped:
        findings.append(
            {
                "level": "warning",
                "title": "Run began with a partial day",
                "message": "The export contains a bootstrap/partial-day marker. Review the opening events before approval.",
            }
        )
    else:
        findings.append(
            {
                "level": "pass",
                "title": "No bootstrap marker",
                "message": "The export does not identify its first recorded day as partial.",
            }
        )

    evidence_mode = current_submission.run.challenge_mode or current_submission.challenge_mode
    if not current_submission.evidence_url and (not evidence_mode or evidence_mode.evidence_required):
        findings.append(
            {
                "level": "warning",
                "title": "No URL or VOD provided",
                "message": "The participant did not attach a cached broadcast or provide a manual URL.",
            }
        )

    baseline = _baseline_for(current_submission)
    challenge_mode = current_submission.challenge_mode
    if not decoded.challenge_id and not decoded.challenge_game_mode:
        findings.append(
            {
                "level": "info",
                "title": "Legacy challenge evidence",
                "message": "This export predates explicit challenge-mode evidence.",
            }
        )
    elif not challenge_mode:
        findings.append(
            {
                "level": "warning",
                "title": "Unmapped challenge mode",
                "message": (
                    "The website does not currently map "
                    f'"{decoded.challenge_id or decoded.challenge_game_mode}".'
                ),
            }
        )
    elif not decoded.challenge_id:
        findings.append(
            {
                "level": "info",
                "title": "Challenge mode recognised by game-mode name",
                "message": (
                    f"{challenge_mode.display_name} matches the exact Project Zomboid "
                    "game-mode name; this save did not expose a challenge ID."
                ),
            }
        )
    elif (
        challenge_mode.game_mode_name
        and decoded.challenge_game_mode != challenge_mode.game_mode_name
    ):
        findings.append(
            {
                "level": "warning",
                "title": "Challenge game-mode name differs",
                "message": (
                    f'ID "{decoded.challenge_id}" maps to {challenge_mode.display_name}, '
                    f'but Project Zomboid reported "{decoded.challenge_game_mode}".'
                ),
            }
        )
    else:
        findings.append(
            {
                "level": "pass",
                "title": "Challenge mode recognised",
                "message": f"{challenge_mode.display_name} matches the exported challenge evidence.",
            }
        )
    if (
        run.starting_challenge_id
        and decoded.challenge_id
        and run.starting_challenge_id != decoded.challenge_id
    ):
        findings.append(
            {
                "level": "danger",
                "title": "Starting challenge mode changed",
                "message": (
                    f'This run began as "{run.starting_challenge_id}" '
                    f'but this submission reports "{decoded.challenge_id}".'
                ),
            }
        )
    comparison = None
    baseline_events = []
    if baseline:
        try:
            baseline_export = decode_run_export_cached(baseline.raw_export)
            baseline_events = baseline_export.events
        except InvalidRunExport as exc:
            findings.append(
                {
                    "level": "danger",
                    "title": "Approved baseline could not be decoded",
                    "message": str(exc),
                }
            )
        else:
            if (
                baseline_export.challenge_id
                and decoded.challenge_id
                and baseline_export.challenge_id != decoded.challenge_id
            ):
                findings.append(
                    {
                        "level": "danger",
                        "title": "Challenge mode changed",
                        "message": (
                            f'The approved baseline reports "{baseline_export.challenge_id}" '
                            f'but this submission reports "{decoded.challenge_id}".'
                        ),
                    }
                )
            common_length = min(len(baseline_events), len(events))
            changed_sequences = [
                index + 1
                for index in range(common_length)
                if baseline_events[index] != events[index]
            ]
            if len(events) < len(baseline_events):
                changed_sequences.extend(range(len(events) + 1, len(baseline_events) + 1))
            if changed_sequences:
                preview = ", ".join(str(value) for value in changed_sequences[:8])
                if len(changed_sequences) > 8:
                    preview += ", …"
                findings.append(
                    {
                        "level": "danger",
                        "title": f"{len(changed_sequences)} previously approved event(s) changed",
                        "message": "This submission changes accepted history. Approval is blocked until the differences are resolved.",
                    }
                )
            else:
                findings.append(
                    {
                        "level": "pass",
                        "title": "Approved history is unchanged",
                        "message": f"All {len(baseline_events):,} previously approved events are preserved.",
                    }
                )
            comparison = {
                "baseline": baseline,
                "event_delta": len(events) - len(baseline_events),
                "kill_delta": current_submission.current_kills - baseline.current_kills,
                "changed_sequences": changed_sequences,
                "changed_events": changed_event_details(baseline_events, events, changed_sequences),
            }
    else:
        findings.append(
            {
                "level": "info",
                "title": "First submission for this run",
                "message": "There is no previously approved snapshot to compare.",
            }
        )

    event_rows = _event_rows(events, baseline_events, current_submission.status == RunSubmission.Status.APPROVED)
    event_findings = {}
    for row in event_rows:
        if row["review_level"] not in {"warning", "info"} or not row["review_reason"]:
            continue
        key = (row["review_level"], row["review_reason"])
        event_findings.setdefault(key, []).append(str(row["sequence"]))
    for (level, reason), sequences in event_findings.items():
        findings.append({
            "level": level,
            "title": reason,
            "message": "Recorded in event(s) " + ", ".join(sequences) + ". See the event ledger below.",
        })

    first_time = _event_time(events[0]) if events else None
    last_time = _event_time(events[-1]) if events else None
    generated_span = last_time - first_time if first_time and last_time else None
    return {
        "current_submission": current_submission,
        "baseline": baseline,
        "comparison": comparison,
        "challenge_mode": challenge_mode,
        "challenge_id": decoded.challenge_id,
        "challenge_game_mode": decoded.challenge_game_mode,
        "findings": findings,
        "severity": review_severity(findings),
        "event_counts": [
            {
                "event_type": event_type,
                "label": EVENT_LABELS.get(
                    event_type, event_type.replace(".", " ").replace("_", " ").title()
                ),
                "count": count,
            }
            for event_type, count in counts.most_common()
        ],
        "event_rows": event_rows,
        "first_event_at": first_time,
        "last_event_at": last_time,
        "generated_span": generated_span,
        "snapshot_json": json.dumps(
            decoded.projection, indent=2, ensure_ascii=False, sort_keys=True
        ),
        "event_history_json": json.dumps(
            events, indent=2, ensure_ascii=False, sort_keys=True
        ),
    }


def build_challenge_run_overview(run):
    approved_events = decode_run_export_cached(run.approved_submission.raw_export).events if run.approved_submission else []
    events = [event for event in (run.latest_events or []) if isinstance(event, dict)]
    counts = Counter(str(event.get("event_type") or "unknown") for event in events)
    return {
        "event_counts": [
            {
                "event_type": event_type,
                "label": EVENT_LABELS.get(
                    event_type, event_type.replace(".", " ").replace("_", " ").title()
                ),
                "count": count,
            }
            for event_type, count in counts.most_common()
        ],
        "event_rows": _event_rows(events, approved_events),
        "snapshot_json": json.dumps(
            run.latest_projection or {}, indent=2, ensure_ascii=False, sort_keys=True
        ),
        "event_history_json": json.dumps(
            events, indent=2, ensure_ascii=False, sort_keys=True
        ),
    }


def capture_preapproval_assessment(submission):
    """Persist the immutable automated assessment created at submission time."""
    if submission.preapproval_assessed_at is not None:
        return submission.preapproval_state
    try:
        review = build_run_review(submission)
        findings = review["findings"]
        state = {
            "pass": RunSubmission.PreapprovalState.GREEN,
            "warning": RunSubmission.PreapprovalState.ORANGE,
            "danger": RunSubmission.PreapprovalState.RED,
        }[review["severity"]]
    except InvalidRunExport as exc:
        state = RunSubmission.PreapprovalState.RED
        findings = [
            {
                "level": "danger",
                "title": "Invalid export",
                "message": str(exc),
            }
        ]
    assessed_at = django_timezone.now()
    RunSubmission.objects.filter(pk=submission.pk).update(
        preapproval_state=state,
        preapproval_findings=findings,
        preapproval_version=1,
        preapproval_assessed_at=assessed_at,
    )
    submission.preapproval_state = state
    submission.preapproval_findings = findings
    submission.preapproval_version = 1
    submission.preapproval_assessed_at = assessed_at
    return state


def current_review_reasons(submission, review=None):
    """Present current review requirements without rewriting historical assessments."""
    if submission.run.lifecycle_status in {"invalidated"} or submission.status not in RunSubmission.moderation_queue_statuses():
        return []
    from .vod_evidence import current_evidence_finding
    evidence_labels = {
        "No URL or VOD provided", "Supply a valid HTTPS Twitch or YouTube VOD link.",
        "The provider could not find accessible video evidence. Correct the link or supply another VOD.",
        "VOD link invalid or unavailable",
    }
    stored_reasons = submission.routing_reasons or [
        finding["title"] for finding in submission.preapproval_findings
        if finding.get("level") in {"warning", "danger"} and finding.get("title")
    ]
    reasons = [reason for reason in stored_reasons
               if reason not in evidence_labels and reason != "First approval for this run"]
    baseline = review["baseline"] if review is not None else _baseline_for(submission)
    if baseline is None:
        reasons.insert(0, "First approval for this run")
    evidence = current_evidence_finding(submission)
    mode = submission.run.challenge_mode or submission.challenge_mode
    if evidence and (submission.evidence_url or mode is None or mode.evidence_required):
        reasons.append(evidence)
    return list(dict.fromkeys(reasons))


def current_review_summary(submission):
    """Summarize current checks while retaining the original stored assessment."""
    try:
        review = build_run_review(submission)
        level = review["severity"]
        details = "; ".join(
            finding["title"] for finding in review["findings"]
            if finding["level"] in {"warning", "danger"}
        )
    except InvalidRunExport as exc:
        level, details = "danger", str(exc)
    return {
        "level": level,
        "label": {"pass": "All checks passed", "warning": "Needs attention", "danger": "Blocking issue"}[level],
        "details": details or "Checked against the current rules and applicable approved baseline.",
    }


def event_field_changes(before, after, path=""):
    """Return changed fields, preserving missing values separately from null."""
    missing = object()
    def compare(old, new, label):
        if isinstance(old, dict) and isinstance(new, dict):
            rows = []
            for key in sorted(old.keys() | new.keys()):
                rows.extend(compare(old.get(key, missing), new.get(key, missing),
                                    f"{label}.{key}" if label else key))
            return rows
        if old == new:
            return []
        def display(value):
            if value is missing:
                return "Not present"
            return json.dumps(value, ensure_ascii=False, indent=2)
        return [{"field": label or "Event", "before": display(old), "after": display(new)}]
    return compare(before, after, path)


def changed_event_details(baseline_events, events, sequences):
    details = []
    for sequence in sequences:
        before = baseline_events[sequence - 1]
        after = events[sequence - 1] if sequence <= len(events) else {}
        event_type = before.get("event_type", "")
        details.append({
            "sequence": sequence,
            "label": EVENT_LABELS.get(event_type, event_type),
            "removed": sequence > len(events),
            "fields": event_field_changes(before, after),
            "after_label": EVENT_LABELS.get(after.get("event_type"), after.get("event_type", "Event missing")),
            "replacement": bool(after) and event_type != after.get("event_type"),
            "before_json": json.dumps(before, ensure_ascii=False, indent=2),
            "after_json": json.dumps(after, ensure_ascii=False, indent=2) if after else "Event removed",
        })
    return details
