import csv
import hashlib
import io
import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import LegacyDataImport, LegacyRun, LegacyRunClaim, LegacyRunSubmission


HEADER_ALIASES = {
    "position": "rank",
    "name": "name",
    "zombieskilled": "kills",
    "survivaltimedays": "days",
    "outpostscleared": "outposts",
    "level10skills": "skills",
    "overallchallengeprogress": "progress",
}
REQUIRED_FIELDS = set(HEADER_ALIASES.values()) - {"rank"}


def _normalise_header(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def normalise_legacy_name(value):
    return " ".join(str(value or "").split()).casefold()


def _decimal(value, label, row_number, maximum=None):
    cleaned = str(value or "").strip().replace(",", "").replace("%", "")
    if not cleaned:
        return Decimal("0")
    try:
        result = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValidationError(f"Row {row_number}: {label} must be a number.") from exc
    if result < 0 or (maximum is not None and result > maximum):
        suffix = f" between 0 and {maximum}" if maximum is not None else " zero or greater"
        raise ValidationError(f"Row {row_number}: {label} must be{suffix}.")
    return result


def decode_csv_upload(upload):
    content = upload.read()
    if len(content) > 5 * 1024 * 1024:
        raise ValidationError("Each legacy CSV must be no larger than 5 MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("Legacy files must be UTF-8 CSV exports.") from exc
    if "\x00" in text:
        raise ValidationError("Legacy files must be text CSV exports.")
    return text


def parse_legacy_csv(text, label):
    rows = list(csv.reader(io.StringIO(text)))
    header_index = None
    field_indexes = {}
    for index, row in enumerate(rows):
        aliases = {
            HEADER_ALIASES[normalised]: position
            for position, cell in enumerate(row)
            if (normalised := _normalise_header(cell)) in HEADER_ALIASES
        }
        if REQUIRED_FIELDS <= set(aliases):
            header_index = index
            field_indexes = aliases
            break
    if header_index is None:
        raise ValidationError(
            f"{label} does not contain the expected Google Sheet column headings."
        )

    parsed = []
    errors = []
    for row_index, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        def cell(field):
            position = field_indexes[field]
            return row[position] if position < len(row) else ""

        name = " ".join(cell("name").split())
        if not name:
            if not any(str(value).strip() for value in row):
                continue
            errors.append(f"Row {row_index}: participant name is required.")
            continue
        try:
            record = {
                "row": row_index,
                "name": name,
                "normalised_name": normalise_legacy_name(name),
                "kills": int(_decimal(cell("kills"), "zombie kills", row_index)),
                "days": str(_decimal(cell("days"), "survival days", row_index)),
                "outposts": int(_decimal(cell("outposts"), "outposts", row_index, 13)),
                "skills": int(_decimal(cell("skills"), "maxed skills", row_index, 35)),
                "progress": str(_decimal(cell("progress"), "challenge progress", row_index, 100)),
            }
            parsed.append(record)
        except ValidationError as exc:
            errors.extend(exc.messages)
    if errors:
        raise ValidationError(errors)
    if not parsed:
        raise ValidationError(f"{label} does not contain any legacy records.")
    return parsed


def _best_record(records):
    return max(
        records,
        key=lambda item: (
            Decimal(item["progress"]), item["kills"], item["outposts"],
            item["skills"], Decimal(item["days"]), -item["row"],
        ),
    )


def _assign_positions(records):
    ranked = sorted(
        (dict(record) for record in records),
        key=lambda item: (
            -Decimal(item["progress"]), -item["kills"], -item["outposts"],
            -item["skills"], -Decimal(item["days"]), item["normalised_name"],
        ),
    )
    for position, record in enumerate(ranked, start=1):
        record["rank"] = position
    return {record["normalised_name"]: record for record in ranked}


def _same_result(left, right):
    fields = ("normalised_name", "kills", "days", "outposts", "skills", "progress")
    return bool(left and right) and all(left[field] == right[field] for field in fields)


def build_legacy_import_preview(leaderboard_text, hall_of_fame_text):
    leaderboard_rows = parse_legacy_csv(leaderboard_text, "Legacy Leaderboard")
    hall_rows = parse_legacy_csv(hall_of_fame_text, "Legacy Hall of Fame")
    leaderboard_groups = {}
    hall_groups = {}
    for row in leaderboard_rows:
        leaderboard_groups.setdefault(row["normalised_name"], []).append(row)
    for row in hall_rows:
        hall_groups.setdefault(row["normalised_name"], []).append(row)

    active_by_name = _assign_positions(
        _best_record(rows) for rows in leaderboard_groups.values()
    )
    hall_best_by_name = {
        name_key: _best_record(rows) for name_key, rows in hall_groups.items()
    }
    merged_best_by_name = _assign_positions(
        _best_record([
            record for record in (
                active_by_name.get(name_key), hall_best_by_name.get(name_key)
            ) if record
        ])
        for name_key in set(active_by_name) | set(hall_best_by_name)
    )

    records = []
    for name_key in sorted(set(active_by_name) | set(merged_best_by_name)):
        active = active_by_name.get(name_key)
        best = merged_best_by_name[name_key]
        display = (active or best)["name"]
        records.append({
            "source_key": hashlib.sha256(name_key.encode("utf-8")).hexdigest(),
            "normalised_name": name_key,
            "legacy_participant_name": display,
            "lifecycle": LegacyRun.Lifecycle.ACTIVE if active else LegacyRun.Lifecycle.INACTIVE,
            "leaderboard": active,
            "hall_of_fame": best,
        })
    duplicate_leaderboard = sum(len(rows) - 1 for rows in leaderboard_groups.values())
    duplicate_hall = sum(len(rows) - 1 for rows in hall_groups.values())
    return {
        "counts": {
            "leaderboard_rows": len(leaderboard_rows),
            "hall_of_fame_rows": len(hall_rows),
            "merged_runs": len(records),
            "active_runs": len(leaderboard_groups),
            "inactive_runs": len(set(hall_groups) - set(leaderboard_groups)),
            "matched_names": len(set(leaderboard_groups) & set(hall_groups)),
            "leaderboard_duplicates": duplicate_leaderboard,
            "hall_of_fame_duplicates": duplicate_hall,
            "leaderboard_positions_assigned": len(active_by_name),
            "hall_of_fame_positions_assigned": len(merged_best_by_name),
        },
        "records": records,
        "warnings": [
            message for message in (
                f"{duplicate_leaderboard} repeated Legacy Leaderboard row(s) were reduced to the strongest record."
                if duplicate_leaderboard else "",
                f"{duplicate_hall} repeated Legacy Hall of Fame row(s) were reduced to the strongest record."
                if duplicate_hall else "",
            ) if message
        ],
    }


def create_legacy_import_review(*, leaderboard_upload, hall_of_fame_upload, uploaded_by):
    leaderboard_text = decode_csv_upload(leaderboard_upload)
    hall_text = decode_csv_upload(hall_of_fame_upload)
    preview = build_legacy_import_preview(leaderboard_text, hall_text)
    return LegacyDataImport.objects.create(
        leaderboard_filename=leaderboard_upload.name[:255],
        hall_of_fame_filename=hall_of_fame_upload.name[:255],
        leaderboard_sha256=hashlib.sha256(leaderboard_text.encode("utf-8")).hexdigest(),
        hall_of_fame_sha256=hashlib.sha256(hall_text.encode("utf-8")).hexdigest(),
        leaderboard_csv=leaderboard_text,
        hall_of_fame_csv=hall_text,
        preview=preview,
        uploaded_by=uploaded_by,
    )


def _create_submission(run, record, source, review, reviewer):
    return LegacyRunSubmission.objects.create(
        run=run,
        status=LegacyRunSubmission.Status.APPROVED,
        source=source,
        source_rank=record["rank"],
        zombie_kills=record["kills"],
        survival_days=Decimal(record["days"]),
        outposts_cleared=record["outposts"],
        maxed_skills=record["skills"],
        challenge_progress=Decimal(record["progress"]),
        import_review=review,
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
        review_note="Approved by the confirmed legacy data import.",
    )


@transaction.atomic
def apply_legacy_import(review, reviewer):
    review = LegacyDataImport.objects.select_for_update().get(pk=review.pk)
    if review.status != LegacyDataImport.Status.PREVIEW:
        raise ValidationError("This legacy data import has already been resolved.")
    preview = build_legacy_import_preview(review.leaderboard_csv, review.hall_of_fame_csv)
    if preview != review.preview:
        raise ValidationError("The stored legacy import no longer matches its validated preview.")
    if LegacyRunClaim.objects.exists() or LegacyRunSubmission.objects.filter(
        source=LegacyRunSubmission.Source.PARTICIPANT
    ).exists():
        raise ValidationError(
            "Legacy records cannot be replaced after claims or participant submissions exist."
        )

    LegacyRun.objects.all().delete()
    for item in preview["records"]:
        run = LegacyRun.objects.create(
            source_key=item["source_key"],
            legacy_participant_name=item["legacy_participant_name"],
            normalized_legacy_name=item["normalised_name"],
            lifecycle=item["lifecycle"],
        )
        current = None
        if item["leaderboard"]:
            current = _create_submission(
                run, item["leaderboard"], LegacyRunSubmission.Source.IMPORT_LEADERBOARD,
                review, reviewer,
            )
        best = None
        if item["hall_of_fame"]:
            if _same_result(item["leaderboard"], item["hall_of_fame"]):
                best = current
            else:
                best = _create_submission(
                    run, item["hall_of_fame"], LegacyRunSubmission.Source.IMPORT_HALL_OF_FAME,
                    review, reviewer,
                )
        run.current_submission = current
        run.best_submission = best or current
        run.save(update_fields=("current_submission", "best_submission", "updated_at"))
    review.preview = preview
    review.status = LegacyDataImport.Status.IMPORTED
    review.imported_at = timezone.now()
    review.save(update_fields=("preview", "status", "imported_at"))
    return review
