import uuid

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
