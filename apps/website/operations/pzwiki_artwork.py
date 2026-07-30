from django.db import transaction

from .models import CatalogueImportReview, PZWikiArtworkSyncJob


@transaction.atomic
def enqueue_pzwiki_artwork_sync(*, catalogue_review, trigger, requested_by=None):
    review = CatalogueImportReview.objects.select_for_update().get(
        pk=catalogue_review.pk
    )
    if review.status != CatalogueImportReview.Status.APPROVED:
        raise ValueError("PZWiki artwork can only be synced for an approved catalogue.")

    active_job = (
        PZWikiArtworkSyncJob.objects.filter(
            catalogue_review=review,
            status__in=(
                PZWikiArtworkSyncJob.Status.QUEUED,
                PZWikiArtworkSyncJob.Status.RUNNING,
            ),
        )
        .order_by("requested_at", "pk")
        .first()
    )
    if active_job:
        return active_job, False

    return (
        PZWikiArtworkSyncJob.objects.create(
            source=review.source,
            catalogue_review=review,
            trigger=trigger,
            requested_by=requested_by,
            summary="PZWiki artwork reconciliation is queued.",
        ),
        True,
    )
