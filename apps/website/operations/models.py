from django.db import models
from django.conf import settings


class RateLimitBucket(models.Model):
    key = models.CharField(max_length=96, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = "operational rate-limit bucket"
        verbose_name_plural = "operational rate-limit buckets"


class WorkerHeartbeatRecord(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    worker_id = models.CharField(max_length=64)
    release_id = models.CharField(max_length=128)
    process_id = models.PositiveIntegerField()
    recorded_at = models.DateTimeField()

    class Meta:
        verbose_name = "worker heartbeat"
        verbose_name_plural = "worker heartbeats"


class ReferenceSource(models.Model):
    class AuthenticationStatus(models.TextChoices):
        NOT_CONFIGURED = "not_configured", "Not configured"
        AUTHENTICATION_REQUIRED = "authentication_required", "Authentication required"
        AUTHENTICATED = "authenticated", "Authenticated"
        ERROR = "error", "Error"

    name = models.CharField(max_length=80, default="Project Zomboid")
    app_id = models.PositiveIntegerField(default=108600, editable=False)
    account_name = models.CharField(max_length=80, blank=True)
    steamcmd_path = models.CharField(max_length=500, blank=True)
    install_root = models.CharField(max_length=500, blank=True)
    authentication_status = models.CharField(
        max_length=32,
        choices=AuthenticationStatus.choices,
        default=AuthenticationStatus.NOT_CONFIGURED,
        editable=False,
    )
    installed_build_id = models.CharField(max_length=32, blank=True, editable=False)
    decompiled_build_id = models.CharField(max_length=32, blank=True, editable=False)
    decompiled_at = models.DateTimeField(null=True, blank=True, editable=False)
    java_executable = models.CharField(max_length=500, blank=True)
    decompiler_jar = models.CharField(max_length=500, blank=True)
    decompiled_root = models.CharField(max_length=500, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_updated_at = models.DateTimeField(null=True, blank=True, editable=False)
    authenticated_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_error = models.TextField(blank=True, editable=False)

    class Meta:
        verbose_name = "Project Zomboid reference source"
        verbose_name_plural = "Project Zomboid reference source"

    def __str__(self):
        return self.name


class RunDataDangerZone(ReferenceSource):
    class Meta:
        proxy = True
        verbose_name = "run data danger zone"
        verbose_name_plural = "run data danger zone"


class ReferenceUpdateJob(models.Model):
    class Operation(models.TextChoices):
        UPDATE = "update", "Steam update"
        DECOMPILE = "decompile", "Decompile"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        UNCHANGED = "unchanged", "No update available"
        UPDATED = "updated", "Updated"
        AUTHENTICATION_REQUIRED = "authentication_required", "Authentication required"
        FAILED = "failed", "Failed"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        SCHEDULED = "scheduled", "Scheduled"

    source = models.ForeignKey(
        ReferenceSource, on_delete=models.PROTECT, related_name="jobs"
    )
    operation = models.CharField(
        max_length=16, choices=Operation.choices, default=Operation.UPDATE
    )
    status = models.CharField(max_length=32, choices=Status.choices)
    trigger = models.CharField(
        max_length=16, choices=Trigger.choices, default=Trigger.MANUAL
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    previous_build_id = models.CharField(max_length=32, blank=True)
    installed_build_id = models.CharField(max_length=32, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ("-requested_at", "-pk")

    def __str__(self):
        return (
            f"{self.source} — {self.get_operation_display()}: "
            f"{self.get_status_display()}"
        )


class CatalogueImportReview(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready for review"
        APPROVED = "approved", "Approved"
        REVERTED = "reverted", "Reverted"
        REJECTED = "rejected", "Rejected"
        STALE = "stale", "Source changed"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        ReferenceSource, on_delete=models.PROTECT, related_name="catalogue_reviews"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    game_version = models.CharField(max_length=32)
    installed_build_id = models.CharField(max_length=32)
    decompiled_build_id = models.CharField(max_length=32)
    install_root = models.CharField(max_length=500)
    decompiled_root = models.CharField(max_length=500)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)
    snapshot = models.JSONField(default=list, blank=True, editable=False)
    diff = models.JSONField(default=dict, blank=True, editable=False)
    class Meta:
        ordering = ("-requested_at", "-pk")
        verbose_name = "catalogue import review"
        verbose_name_plural = "catalogue import reviews"

    def __str__(self):
        return f"Build {self.installed_build_id} catalogue - {self.get_status_display()}"


class PZWikiArtworkSyncJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class Trigger(models.TextChoices):
        CATALOGUE_APPROVAL = "catalogue_approval", "Catalogue approval"
        MANUAL = "manual", "Manual"

    source = models.ForeignKey(
        ReferenceSource, on_delete=models.PROTECT, related_name="pzwiki_artwork_jobs"
    )
    catalogue_review = models.ForeignKey(
        CatalogueImportReview,
        on_delete=models.PROTECT,
        related_name="pzwiki_artwork_jobs",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED
    )
    trigger = models.CharField(max_length=24, choices=Trigger.choices)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)
    unavailable_artwork = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-requested_at", "-pk")
        verbose_name = "PZWiki artwork sync job"
        verbose_name_plural = "PZWiki artwork sync jobs"
        constraints = [
            models.UniqueConstraint(
                fields=("catalogue_review",),
                condition=models.Q(status__in=("queued", "running")),
                name="operations_one_active_pzwiki_job_per_review",
            )
        ]

    def __str__(self):
        return (
            f"Catalogue review #{self.catalogue_review_id} artwork - "
            f"{self.get_status_display()}"
        )
