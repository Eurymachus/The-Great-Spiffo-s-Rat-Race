import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class ParticipantManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, nickname, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not nickname:
            raise ValueError("A participant nickname is required.")
        email = self.normalize_email(email).casefold()
        participant = self.model(email=email, nickname=nickname, **extra_fields)
        participant.set_password(password)
        participant.save(using=self._db)
        return participant

    def create_superuser(self, email, nickname, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", Participant.Status.VERIFIED)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser must have staff and superuser access.")
        return self.create_user(email, nickname, password, **extra_fields)


class Participant(AbstractUser):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending verification"
        VERIFIED = "verified", "Verified"
        EXPIRED = "expired", "Expired"
        DISABLED = "disabled", "Disabled"
        REMOVED = "removed", "Removed"

    class AvatarStatus(models.TextChoices):
        NONE = "none", "No avatar"
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Declined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    nickname = models.CharField(max_length=40)
    normalized_nickname = models.CharField(max_length=40, unique=True, editable=False)
    email = models.EmailField(unique=True)
    normalized_email = models.EmailField(unique=True, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    registered_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    privacy_notice_acknowledged_at = models.DateTimeField(null=True, blank=True)
    privacy_notice_version = models.CharField(max_length=20, blank=True)
    age_eligibility_confirmed_at = models.DateTimeField(null=True, blank=True)
    age_policy_version = models.CharField(max_length=20, blank=True)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    deletion_request_reference = models.UUIDField(null=True, blank=True, editable=False)
    deletion_request_note = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="participant_avatars/", blank=True)
    avatar_status = models.CharField(
        max_length=16, choices=AvatarStatus.choices, default=AvatarStatus.NONE
    )
    avatar_review_path = models.CharField(max_length=255, blank=True, editable=False)
    avatar_moderation_note = models.CharField(max_length=255, blank=True, editable=False)
    avatar_submitted_at = models.DateTimeField(null=True, blank=True)
    primary_streaming_account = models.ForeignKey(
        "StreamingAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for_participants",
        help_text="The connected Twitch or YouTube channel shown on public rankings.",
    )

    objects = ParticipantManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    class Meta:
        ordering = ("-registered_at",)

    def save(self, *args, **kwargs):
        self.nickname = self.nickname.strip()
        self.email = self.email.strip().casefold()
        self.normalized_nickname = self.nickname.casefold()
        self.normalized_email = self.email.casefold()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.avatar:
            self.avatar.delete(save=False)
        if self.avatar_review_path:
            (Path(settings.AVATAR_QUARANTINE_ROOT) / self.avatar_review_path).unlink(missing_ok=True)
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.nickname


class AccountClosureRecord(models.Model):
    reference = models.UUIDField(primary_key=True, editable=False)
    requested_at = models.DateTimeField()
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-processed_at",)

    def __str__(self):
        return f"Closure {self.reference}"


class Notification(models.Model):
    class Category(models.TextChoices):
        ACCOUNT = "account", "Account"
        SUBMISSION = "submission", "Submission"
        EVENT = "event", "Event"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="notifications"
    )
    category = models.CharField(
        max_length=16, choices=Category.choices, default=Category.ACCOUNT
    )
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=300)
    destination = models.CharField(
        max_length=500, blank=True,
        help_text="Optional local path opened when the notification is selected.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.recipient}: {self.title}"

    @property
    def is_read(self):
        return self.read_at is not None


class StreamingAccount(models.Model):
    class Provider(models.TextChoices):
        DISCORD = "discord", "Discord"
        TWITCH = "twitch", "Twitch"
        YOUTUBE = "youtube", "YouTube"

    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        RECONNECT_REQUIRED = "reconnect_required", "Reconnect required"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="streaming_accounts",
    )
    provider = models.CharField(max_length=16, choices=Provider.choices)
    provider_identity = models.CharField(
        max_length=255,
        help_text="The provider's immutable account identifier.",
    )
    channel_identity = models.CharField(
        max_length=255,
        help_text="The immutable broadcaster or channel identifier.",
    )
    display_name = models.CharField(max_length=255)
    channel_url = models.URLField(max_length=500)
    granted_scopes = models.JSONField(default=list, blank=True)
    provider_metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.CONNECTED,
    )
    connected_at = models.DateTimeField(auto_now_add=True)
    refreshed_at = models.DateTimeField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    encrypted_access_token = models.TextField(blank=True, editable=False)
    encrypted_refresh_token = models.TextField(blank=True, editable=False)
    token_validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "platform integration"
        verbose_name_plural = "platform integrations"
        ordering = ("provider",)
        constraints = (
            models.UniqueConstraint(
                fields=("participant", "provider"),
                name="unique_streaming_provider_per_participant",
            ),
            models.UniqueConstraint(
                fields=("provider", "provider_identity"),
                name="unique_streaming_provider_identity",
            ),
            models.UniqueConstraint(
                fields=("provider", "channel_identity"),
                name="unique_streaming_channel_identity",
            ),
        )

    def __str__(self):
        return f"{self.participant} — {self.get_provider_display()}"


class StreamingMedia(models.Model):
    class Kind(models.TextChoices):
        VIDEO = "video", "Video"
        CLIP = "clip", "Clip"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        StreamingAccount, on_delete=models.CASCADE, related_name="media"
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    provider_media_id = models.CharField(max_length=255)
    parent_media_id = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=500, blank=True)
    canonical_url = models.URLField(max_length=1000)
    thumbnail_url = models.URLField(max_length=1000, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    vod_offset_seconds = models.PositiveIntegerField(null=True, blank=True)
    metadata_snapshot = models.JSONField(default=dict, blank=True)
    refreshed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "cached streaming media"
        verbose_name_plural = "cached streaming media"
        ordering = ("-published_at", "kind", "provider_media_id")
        constraints = (
            models.UniqueConstraint(
                fields=("account", "kind", "provider_media_id"),
                name="unique_streaming_media_per_account",
            ),
        )

    def __str__(self):
        return self.title or self.provider_media_id


class WorkshopMod(models.Model):
    class Ruling(models.TextChoices):
        REQUIRED = "required", "Required"
        ALLOWED = "allowed", "Allowed"
        DISALLOWED = "disallowed", "Disallowed"
        PENDING = "pending", "Pending review"

    class PreviousUnstableRuling(models.TextChoices):
        ALLOWED = "allowed", "Allowed"
        DISALLOWED = "disallowed", "Disallowed"
        NOT_REVIEWED = "not_reviewed", "Not reviewed"
        UNKNOWN = "unknown", "Unknown"

    workshop_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    steam_url = models.URLField(max_length=500)
    preview_url = models.URLField(max_length=1000, blank=True)
    creator_steam_id = models.CharField(max_length=32, blank=True)
    ruling = models.CharField(
        max_length=16,
        choices=Ruling.choices,
        default=Ruling.PENDING,
        db_index=True,
    )
    is_recommended = models.BooleanField(
        default=False,
        help_text="Feature this Allowed mod in the public Recommended section.",
    )
    public_rationale = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "Participant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_workshop_mods",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    previous_unstable_ruling = models.CharField(
        max_length=16,
        choices=PreviousUnstableRuling.choices,
        default=PreviousUnstableRuling.NOT_REVIEWED,
    )
    unstable_ruling_notes = models.TextField(blank=True)
    submission_reason = models.TextField(blank=True)
    submitted_by = models.ForeignKey(
        "Participant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="submitted_workshop_mods",
    )
    steam_checked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "workshop_id")
        verbose_name = "Workshop mod"
        verbose_name_plural = "Workshop mods"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(is_recommended=False) | models.Q(ruling="allowed"),
                name="recommended_workshop_mod_is_allowed",
            ),
        )

    def __str__(self):
        return self.title


class WorkshopModVote(models.Model):
    class Decision(models.TextChoices):
        ALLOW = "allow", "Allow"
        DISALLOW = "disallow", "Disallow"
        DISCUSS = "discuss", "Discuss"

    workshop_mod = models.ForeignKey(
        WorkshopMod,
        on_delete=models.CASCADE,
        related_name="team_votes",
    )
    voter = models.ForeignKey(
        "Participant",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="workshop_mod_votes",
    )
    voter_name = models.CharField(max_length=150)
    decision = models.CharField(max_length=16, choices=Decision.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("workshop_mod", "voter"),
                name="one_vote_per_team_member_per_workshop_mod",
            ),
        )

    def __str__(self):
        return f"{self.voter_name}: {self.get_decision_display()}"


class ChallengeMode(models.Model):
    key = models.CharField(
        max_length=160,
        unique=True,
        help_text="The exact challenge ID exported by Project Zomboid.",
    )
    display_name = models.CharField(max_length=160)
    game_mode_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="The expected Project Zomboid game-mode name, retained for comparison.",
    )
    description = models.TextField(blank=True)
    max_active_runs_per_participant = models.PositiveSmallIntegerField(
        default=1,
        help_text=(
            "Maximum active runs each participant may have in this challenge mode. "
            "Updates to an existing active run do not use another slot."
        ),
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "display_name", "key")
        verbose_name = "challenge mode"
        verbose_name_plural = "challenge modes"

    def __str__(self):
        return self.display_name


class ChallengeModeAlias(models.Model):
    challenge_mode = models.ForeignKey(
        ChallengeMode, on_delete=models.CASCADE, related_name="aliases"
    )
    key = models.CharField(
        max_length=160,
        unique=True,
        help_text="An exact historical or alternative challenge ID.",
    )

    class Meta:
        ordering = ("key",)
        verbose_name = "challenge mode alias"
        verbose_name_plural = "challenge mode aliases"

    def __str__(self):
        return self.key


class ChallengeRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending first approval"
        OFFICIAL = "official", "Verified"

    class Lifecycle(models.TextChoices):
        ACTIVE = "active", "Active"
        DECEASED = "deceased", "Deceased"
        ABANDONED = "abandoned", "Abandoned"
        COMPLETED = "completed", "Completed"
        INVALIDATED = "invalidated", "Invalidated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="challenge_runs",
    )
    run_id = models.CharField(max_length=160, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    approved_submission = models.ForeignKey(
        "RunSubmission",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    challenge_mode = models.ForeignKey(
        ChallengeMode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="runs",
    )
    challenge_id = models.CharField(max_length=160, blank=True)
    challenge_game_mode = models.CharField(max_length=255, blank=True)
    starting_challenge_mode = models.ForeignKey(
        ChallengeMode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="starting_runs",
    )
    starting_challenge_id = models.CharField(max_length=160, blank=True)
    starting_challenge_game_mode = models.CharField(max_length=255, blank=True)
    lifecycle_status = models.CharField(
        max_length=16, choices=Lifecycle.choices, default=Lifecycle.ACTIVE
    )
    participant_deactivated_at = models.DateTimeField(null=True, blank=True)
    export_format = models.PositiveSmallIntegerField()
    generated_at = models.DateTimeField()
    current_kills = models.PositiveBigIntegerField(default=0)
    event_sequence = models.PositiveBigIntegerField(default=0)
    event_hash = models.CharField(max_length=64)
    character_name = models.CharField(max_length=160, blank=True)
    bootstrapped = models.BooleanField(default=False)
    latest_projection = models.JSONField(default=dict, blank=True)
    latest_events = models.JSONField(default=list, blank=True)
    first_submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self):
        return self.character_name or self.run_id

    @property
    def in_game_day(self):
        events = self.latest_events or []
        if not events and self.approved_submission_id:
            from .run_exports import InvalidRunExport, decode_run_export

            try:
                events = decode_run_export(self.approved_submission.raw_export).events
            except InvalidRunExport:
                events = []
        world_ages = [
            event.get("world_age_hours")
            for event in events
            if isinstance(event, dict)
            and isinstance(event.get("world_age_hours"), (int, float))
        ]
        return max(1, int(max(world_ages) // 24) + 1) if world_ages else None

    @property
    def approved_submission_count(self):
        return sum(
            submission.status == RunSubmission.Status.APPROVED
            for submission in self.submissions.all()
        )

    @property
    def challenge_mode_display(self):
        if self.challenge_mode_id:
            return self.challenge_mode.display_name
        if self.challenge_id:
            return f"{self.challenge_id} (Unmapped)"
        return "Legacy / Unspecified"


class LegacyRun(models.Model):
    class Lifecycle(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DECEASED = "deceased", "Deceased"

    source_key = models.CharField(max_length=64, unique=True)
    legacy_participant_name = models.CharField(max_length=160, db_index=True)
    normalized_legacy_name = models.CharField(max_length=160, unique=True, editable=False)
    lifecycle = models.CharField(
        max_length=16, choices=Lifecycle.choices, default=Lifecycle.ACTIVE, db_index=True
    )
    character_name = models.CharField(max_length=160, blank=True)
    claimed_participant = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_legacy_runs",
    )
    current_submission = models.ForeignKey(
        "LegacyRunSubmission", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="current_for_runs",
    )
    best_submission = models.ForeignKey(
        "LegacyRunSubmission", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="best_for_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("legacy_participant_name",)
        verbose_name = "legacy run"
        verbose_name_plural = "legacy runs"

    def __str__(self):
        return self.claimed_participant.nickname if self.claimed_participant_id else self.legacy_participant_name


class LegacyRunSubmission(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"

    class Source(models.TextChoices):
        IMPORT_LEADERBOARD = "import_leaderboard", "Imported Legacy Leaderboard"
        IMPORT_HALL_OF_FAME = "import_hall_of_fame", "Imported Legacy Hall of Fame"
        PARTICIPANT = "participant", "Participant submission"

    run = models.ForeignKey(LegacyRun, on_delete=models.CASCADE, related_name="submissions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    source = models.CharField(max_length=24, choices=Source.choices)
    source_rank = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    character_name = models.CharField(max_length=160, blank=True)
    zombie_kills = models.PositiveBigIntegerField(default=0)
    survival_days = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    outposts_cleared = models.PositiveSmallIntegerField(default=0)
    maxed_skills = models.PositiveSmallIntegerField(default=0)
    challenge_progress = models.DecimalField(max_digits=8, decimal_places=5, default=0)
    survival_time_input = models.CharField(max_length=255, blank=True)
    survival_time_full = models.CharField(max_length=32, blank=True)
    reports_death = models.BooleanField(default=False)
    import_review = models.ForeignKey(
        "LegacyDataImport", null=True, blank=True, on_delete=models.PROTECT,
        related_name="created_submissions",
    )
    submitted_by = models.ForeignKey(
        Participant, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="legacy_run_submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        Participant, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reviewed_legacy_run_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    evidence_provider = models.CharField(max_length=16, blank=True)
    evidence_media_type = models.CharField(max_length=12, blank=True)
    evidence_media_id = models.CharField(max_length=255, blank=True)
    evidence_url = models.URLField(max_length=1000, blank=True)
    evidence_title = models.CharField(max_length=500, blank=True)
    evidence_start_seconds = models.PositiveIntegerField(null=True, blank=True)
    evidence_end_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"{self.run}: {self.get_source_display()}"


class LegacyDataImport(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "preview", "Awaiting confirmation"
        IMPORTED = "imported", "Imported"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PREVIEW)
    leaderboard_filename = models.CharField(max_length=255)
    hall_of_fame_filename = models.CharField(max_length=255)
    leaderboard_sha256 = models.CharField(max_length=64)
    hall_of_fame_sha256 = models.CharField(max_length=64)
    leaderboard_csv = models.TextField()
    hall_of_fame_csv = models.TextField()
    preview = models.JSONField(default=dict)
    uploaded_by = models.ForeignKey(
        Participant, null=True, on_delete=models.SET_NULL, related_name="legacy_data_imports"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    imported_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-uploaded_at",)
        verbose_name = "legacy data import"
        verbose_name_plural = "legacy data imports"

    def __str__(self):
        return f"Legacy import {self.uploaded_at:%Y-%m-%d %H:%M}"


class LegacyRunClaim(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"

    run = models.ForeignKey(
        LegacyRun, on_delete=models.CASCADE, related_name="claims"
    )
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="legacy_run_claims"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    evidence = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_legacy_run_claims",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("run", "participant"), name="unique_legacy_run_participant_claim"
            )
        ]

    def __str__(self):
        return f"{self.participant.nickname}: {self.run.legacy_participant_name}"


class RunSubmission(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        ChallengeRun, on_delete=models.CASCADE, related_name="submissions"
    )
    baseline_submission = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="successor_submissions",
    )
    submitter = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="run_submissions",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RECEIVED
    )
    checksum = models.CharField(max_length=64, unique=True)
    raw_export = models.TextField()
    export_format = models.PositiveSmallIntegerField()
    generated_at = models.DateTimeField()
    current_kills = models.PositiveBigIntegerField(default=0)
    event_sequence = models.PositiveBigIntegerField(default=0)
    event_hash = models.CharField(max_length=64)
    projection = models.JSONField(default=dict, blank=True)
    challenge_mode = models.ForeignKey(
        ChallengeMode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    challenge_id = models.CharField(max_length=160, blank=True)
    challenge_game_mode = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    evidence_provider = models.CharField(max_length=16, blank=True)
    evidence_media_type = models.CharField(max_length=12, blank=True)
    evidence_media_id = models.CharField(max_length=255, blank=True)
    evidence_url = models.URLField(max_length=1000, blank=True)
    evidence_title = models.CharField(max_length=500, blank=True)
    evidence_start_seconds = models.PositiveIntegerField(null=True, blank=True)
    evidence_end_seconds = models.PositiveIntegerField(null=True, blank=True)
    evidence_clips = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"{self.run} — {self.get_status_display()}"

    @property
    def challenge_mode_display(self):
        if self.challenge_mode_id:
            return self.challenge_mode.display_name
        if self.challenge_id:
            return f"{self.challenge_id} (Unmapped)"
        return "Legacy / Unspecified"
