from .models import RunSubmissionEvidenceRevision


EVIDENCE_FIELDS = (
    "evidence_provider",
    "evidence_media_type",
    "evidence_media_id",
    "evidence_url",
    "evidence_title",
    "evidence_start_seconds",
    "evidence_end_seconds",
    "evidence_clips",
)


def evidence_values(submission):
    return {field: getattr(submission, field) for field in EVIDENCE_FIELDS}


def record_evidence_revision(submission, source):
    return RunSubmissionEvidenceRevision.objects.create(
        submission=submission,
        source=source,
        **evidence_values(submission),
    )
