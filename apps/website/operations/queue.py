from django.db import transaction
from django.utils import timezone

from .models import ReferenceSource, ReferenceUpdateJob


ACTIVE_STATUSES = (
    ReferenceUpdateJob.Status.QUEUED,
    ReferenceUpdateJob.Status.RUNNING,
)


@transaction.atomic
def enqueue_reference_update(
    source: ReferenceSource,
    *,
    operation=ReferenceUpdateJob.Operation.UPDATE,
    trigger=ReferenceUpdateJob.Trigger.MANUAL,
    requested_by=None,
):
    ReferenceSource.objects.select_for_update().get(pk=source.pk)
    active = (
        ReferenceUpdateJob.objects.filter(
            source=source, operation=operation, status__in=ACTIVE_STATUSES
        )
        .order_by("requested_at", "pk")
        .first()
    )
    if active:
        return active, False
    return (
        ReferenceUpdateJob.objects.create(
            source=source,
            operation=operation,
            status=ReferenceUpdateJob.Status.QUEUED,
            trigger=trigger,
            requested_by=requested_by,
        ),
        True,
    )


@transaction.atomic
def claim_next_reference_update():
    job = (
        ReferenceUpdateJob.objects.select_for_update()
        .filter(status=ReferenceUpdateJob.Status.QUEUED)
        .order_by("requested_at", "pk")
        .first()
    )
    if not job:
        return None
    job.status = ReferenceUpdateJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=("status", "started_at"))
    return job
