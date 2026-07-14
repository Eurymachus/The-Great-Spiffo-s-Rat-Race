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
    consented_at = models.DateTimeField(null=True, blank=True)
    privacy_notice_version = models.CharField(max_length=20, blank=True)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
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
