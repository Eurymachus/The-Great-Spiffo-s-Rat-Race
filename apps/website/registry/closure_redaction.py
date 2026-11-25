"""Reviewed first-release redaction, without changing retained result values."""
import csv
import hashlib
import io
import json
import uuid

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.utils import timezone

from .legacy_imports import HEADER_ALIASES, REQUIRED_FIELDS, _normalise_header, normalise_legacy_name
from .models import (
    LegacyDataImport, LegacyRun, LegacyRunClaim, LegacyRunSubmission,
    Participant, WorkshopMod, WorkshopModVote,
)


REVIEWABLE_RELATIONS = {
    ("registry.legacyrun", "claimed_participant"),
    ("registry.legacyrunclaim", "participant"),
    ("registry.legacyrunclaim", "reviewed_by"),
    ("registry.legacyrunsubmission", "submitted_by"),
    ("registry.legacyrunsubmission", "reviewed_by"),
    ("registry.workshopmod", "submitted_by"),
    ("registry.workshopmod", "reviewed_by"),
    ("registry.workshopmodvote", "voter"),
}
SALT = "registry.account-closure-redaction.v1"


def _rows(queryset, lock):
    if lock:
        queryset = queryset.select_for_update()
    return list(queryset.order_by("pk").values())


def _remove_csv_rows(text, names):
    """Remove entire matched source rows, including ignored provider columns."""
    from .retention import AccountDeletionBlocked

    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error as exc:
        raise AccountDeletionBlocked("A stored import has invalid CSV and requires source review.") from exc
    name_index = None
    retained = []
    removed = False
    for row in rows:
        columns = {
            HEADER_ALIASES[_normalise_header(value)]: index
            for index, value in enumerate(row) if _normalise_header(value) in HEADER_ALIASES
        }
        if REQUIRED_FIELDS <= set(columns):
            name_index = columns["name"]
        elif name_index is not None and name_index < len(row) and normalise_legacy_name(row[name_index]) in names:
            removed = True
            continue
        retained.append(row)
    if text.strip() and name_index is None:
        raise AccountDeletionBlocked("A stored import has unrecognised columns and requires source review.")
    if not removed:
        return text, False
    output = io.StringIO(newline="")
    csv.writer(output).writerows(retained)
    return output.getvalue(), True


def _import_changes(record, names):
    from .retention import AccountDeletionBlocked

    board, removed_board = _remove_csv_rows(record["leaderboard_csv"], names)
    hall, removed_hall = _remove_csv_rows(record["hall_of_fame_csv"], names)
    preview = record["preview"] or {}
    if not isinstance(preview, dict):
        raise AccountDeletionBlocked("A stored import has an invalid preview and requires source review.")
    records = preview.get("records", [])
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise AccountDeletionBlocked("A stored import has invalid preview records and requires source review.")
    retained = [item for item in records if not (
        normalise_legacy_name(item.get("normalised_name")) in names
        or normalise_legacy_name(item.get("legacy_participant_name")) in names
    )]
    if not (removed_board or removed_hall or len(retained) != len(records)):
        return None
    return {
        "leaderboard_csv": board, "hall_of_fame_csv": hall,
        "leaderboard_filename": "retained-leaderboard.csv",
        "hall_of_fame_filename": "retained-hall-of-fame.csv",
        "leaderboard_sha256": hashlib.sha256(board.encode("utf-8")).hexdigest(),
        "hall_of_fame_sha256": hashlib.sha256(hall.encode("utf-8")).hexdigest(),
        "preview": {"records": retained, "counts": {}, "warnings": [
            "Personal source rows were removed following account closure. This import cannot be applied again."
        ]},
    }


def build_redaction_plan(participant, *, lock=False):
    runs = _rows(LegacyRun.objects.filter(claimed_participant=participant), lock)
    run_ids = [row["id"] for row in runs]
    submissions = _rows(LegacyRunSubmission.objects.filter(
        Q(run_id__in=run_ids) | Q(submitted_by=participant) | Q(reviewed_by=participant)
    ), lock)
    claims = _rows(LegacyRunClaim.objects.filter(
        Q(run_id__in=run_ids) | Q(participant=participant) | Q(reviewed_by=participant)
    ), lock)
    mods = _rows(WorkshopMod.objects.filter(Q(submitted_by=participant) | Q(reviewed_by=participant)), lock)
    votes = _rows(WorkshopModVote.objects.filter(voter=participant), lock)
    names = {normalise_legacy_name(row["legacy_participant_name"]) for row in runs}
    imports = []
    changes = {}
    if names:
        # Include all snapshots, including rejected and unapplied imports, so a
        # former identity cannot survive in an older source review.
        imports = _rows(LegacyDataImport.objects.all(), lock)
        for record in imports:
            update = _import_changes(record, names)
            if update:
                changes[record["id"]] = update

    log_filter = Q(content_type=ContentType.objects.get_for_model(Participant), object_id=str(participant.pk))
    for model, rows in ((LegacyRun, runs), (LegacyRunSubmission, submissions), (LegacyRunClaim, claims),
                        (WorkshopMod, mods), (WorkshopModVote, votes)):
        if rows:
            log_filter |= Q(content_type=ContentType.objects.get_for_model(model), object_id__in=[str(row["id"]) for row in rows])
    logs = _rows(LogEntry.objects.filter(log_filter), lock)
    # Any other participant's hold protects the shared evidence touched here.
    related_ids = set()
    for row in submissions + claims + mods:
        for field in ("participant_id", "submitted_by_id", "reviewed_by_id"):
            if row.get(field):
                related_ids.add(row[field])
    holds = _rows(Participant.objects.filter(pk__in=related_ids, retention_hold=True), lock)
    snapshot = {
        "account": {"id": participant.pk, "requested": participant.deletion_requested_at, "hold": participant.retention_hold},
        "runs": runs, "submissions": submissions, "claims": claims,
        "mods": mods, "votes": votes, "imports": imports, "logs": logs, "holds": holds,
    }
    digest = hashlib.sha256(json.dumps(snapshot, cls=DjangoJSONEncoder, sort_keys=True).encode()).hexdigest()
    return {"snapshot": snapshot, "digest": digest, "import_changes": changes,
            "has_history": bool(runs or submissions or claims or mods or votes),
            "counts": {"runs": len(runs), "submissions": len(submissions), "claims": len(claims),
                       "mods": len(mods), "votes": len(votes), "imports": len(changes), "logs": len(logs)}}


def review_token(participant, plan):
    return signing.dumps({"participant": str(participant.pk), "digest": plan["digest"]}, salt=SALT)


def review_details(plan):
    """Show concrete affected records, never the other rows of shared imports."""
    snapshot = plan["snapshot"]
    details = {key: snapshot[key] for key in ("runs", "submissions", "claims", "mods", "votes", "logs")}
    details["imports"] = []
    for record in snapshot["imports"]:
        update = plan["import_changes"].get(record["id"])
        if not update:
            continue
        removed = {"id": record["id"]}
        for field in ("leaderboard_csv", "hall_of_fame_csv"):
            retained = {tuple(row) for row in csv.reader(io.StringIO(update[field]))}
            removed[field] = [row for row in csv.reader(io.StringIO(record[field])) if tuple(row) not in retained]
        details["imports"].append(removed)
    return json.dumps(details, cls=DjangoJSONEncoder, indent=2, sort_keys=True)


def validate_review(participant, plan, token):
    from .retention import AccountDeletionBlocked

    try:
        reviewed = signing.loads(token, salt=SALT, max_age=3600)
    except signing.BadSignature as exc:
        raise AccountDeletionBlocked("Review the redaction preview again before closing this account.") from exc
    if reviewed != {"participant": str(participant.pk), "digest": plan["digest"]}:
        raise AccountDeletionBlocked("Related records changed. Review the redaction preview again.")
    if plan["snapshot"]["holds"]:
        raise AccountDeletionBlocked("A retention hold protects related evidence.")


def apply_redaction(participant, plan):
    """Run only inside close_account's transaction after validating its review."""
    now = timezone.now()
    snapshot = plan["snapshot"]
    run_ids = {row["id"] for row in snapshot["runs"]}
    personal_submissions = [row["id"] for row in snapshot["submissions"]
                            if row["run_id"] in run_ids or row["submitted_by_id"] == participant.pk]
    personal_claims = [row["id"] for row in snapshot["claims"]
                      if row["run_id"] in run_ids or row["participant_id"] == participant.pk]
    for record in snapshot["runs"]:
        anonymous_key = uuid.uuid4().hex
        LegacyRun.objects.filter(pk=record["id"]).update(
            identity_removed=True, claimed_participant=None,
            legacy_participant_name="Former Rat Racer", normalized_legacy_name=f"removed-{anonymous_key}",
            source_key=anonymous_key, character_name="",
        )
    LegacyRunSubmission.objects.filter(pk__in=personal_submissions).update(
        character_name="", survival_time_input="", review_note="",
        evidence_provider="", evidence_media_type="", evidence_media_id="", evidence_url="", evidence_title="",
        evidence_start_seconds=None, evidence_end_seconds=None,
    )
    # Detach only this account's links; another submitter/reviewer remains intact.
    LegacyRunSubmission.objects.filter(submitted_by=participant).update(submitted_by=None)
    LegacyRunSubmission.objects.filter(reviewed_by=participant).update(reviewed_by=None, review_note="")
    LegacyRunSubmission.objects.filter(run_id__in=[row["id"] for row in snapshot["runs"]], status="received").update(
        status=LegacyRunSubmission.Status.DECLINED, reviewed_at=now,
    )
    LegacyRunClaim.objects.filter(pk__in=personal_claims).update(evidence="", review_note="")
    LegacyRunClaim.objects.filter(run_id__in=[row["id"] for row in snapshot["runs"]], status="pending").update(
        status=LegacyRunClaim.Status.DECLINED, reviewed_at=now,
    )
    LegacyRunClaim.objects.filter(reviewed_by=participant).update(reviewed_by=None, review_note="")
    # Own claims have no retained scoring role and must not keep a participant link.
    LegacyRunClaim.objects.filter(participant=participant).delete()
    WorkshopMod.objects.filter(pk__in=[row["id"] for row in snapshot["mods"]]).update(
        public_rationale="", unstable_ruling_notes="",
    )
    WorkshopMod.objects.filter(submitted_by=participant).update(submitted_by=None, submission_reason="")
    WorkshopMod.objects.filter(reviewed_by=participant).update(reviewed_by=None)
    WorkshopModVote.objects.filter(voter=participant).update(voter=None, voter_name="Former Rat Racer", reason="")
    for pk, update in plan["import_changes"].items():
        LegacyDataImport.objects.filter(pk=pk).update(**update, redacted_at=now)
    logs = LogEntry.objects.filter(pk__in=[row["id"] for row in snapshot["logs"]])
    logs.update(object_repr="Redacted record", change_message="Personal details removed following account closure.")
    logs.filter(content_type=ContentType.objects.get_for_model(Participant), object_id=str(participant.pk)).update(object_id=None)
