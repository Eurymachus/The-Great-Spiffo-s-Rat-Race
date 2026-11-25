from django.shortcuts import get_object_or_404

from .models import LegacyRun, LegacyRunClaim, Participant


def lock_review_record(record):
    """Within an atomic block, lock account, run, then evidence without joins."""
    participant_id = record.participant_id if isinstance(record, LegacyRunClaim) else record.submitted_by_id
    if participant_id:
        get_object_or_404(Participant.objects.select_for_update(), pk=participant_id)
    run = get_object_or_404(LegacyRun.objects.select_for_update(), pk=record.run_id)
    record = get_object_or_404(type(record).objects.select_for_update(), pk=record.pk)
    return record, run
