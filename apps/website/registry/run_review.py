import json
from collections import Counter
from datetime import datetime, timezone

from .models import RunSubmission
from .run_exports import InvalidRunExport, decode_run_export
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


def _event_rows(events):
    rows = []
    for event in events:
        event_type = str(event.get("event_type") or "unknown")
        rows.append(
            {
                "sequence": event.get("sequence"),
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
    return current_submission.baseline_submission


def build_run_review(current_submission):
    run = current_submission.run
    decoded = decode_run_export(current_submission.raw_export)
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

    baseline = _baseline_for(current_submission)
    comparison = None
    baseline_events = []
    if baseline:
        try:
            baseline_export = decode_run_export(baseline.raw_export)
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
                        "title": "Previously approved history changed",
                        "message": f"Approved event sequence(s) {preview} differ from this snapshot.",
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
            }
    else:
        findings.append(
            {
                "level": "info",
                "title": "First submission for this run",
                "message": "There is no previously approved snapshot to compare.",
            }
        )

    first_time = _event_time(events[0]) if events else None
    last_time = _event_time(events[-1]) if events else None
    generated_span = last_time - first_time if first_time and last_time else None
    return {
        "current_submission": current_submission,
        "baseline": baseline,
        "comparison": comparison,
        "findings": findings,
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
        "event_rows": _event_rows(events),
        "first_event_at": first_time,
        "last_event_at": last_time,
        "generated_span": generated_span,
        "raw_json": json.dumps(events, indent=2, ensure_ascii=False, sort_keys=True),
    }
