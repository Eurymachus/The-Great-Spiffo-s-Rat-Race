from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.utils import OperationalError, ProgrammingError


class WebsiteSettings(models.Model):
    SINGLETON_PK = 1
    DEFAULT_MAXIMUM_IMAGE_UPLOAD_SIZE_MB = 10

    id = models.PositiveSmallIntegerField(
        primary_key=True, default=SINGLETON_PK, editable=False
    )
    maximum_image_upload_size = models.PositiveSmallIntegerField(
        "maximum image upload size (MB)",
        default=DEFAULT_MAXIMUM_IMAGE_UPLOAD_SIZE_MB,
        validators=(MinValueValidator(1), MaxValueValidator(100)),
        help_text="The largest individual image accepted by the media library, from 1 to 100 MB.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "website settings"
        verbose_name_plural = "website settings"

    def __str__(self):
        return "Website settings"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        return super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        try:
            settings, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
            return settings
        except (OperationalError, ProgrammingError):
            return None

    @classmethod
    def maximum_image_upload_size_mb(cls):
        settings = cls.current()
        return (
            settings.maximum_image_upload_size
            if settings
            else cls.DEFAULT_MAXIMUM_IMAGE_UPLOAD_SIZE_MB
        )


class ProviderConfiguration(models.Model):
    class Provider(models.TextChoices):
        DISCORD = 'discord', 'Discord'
        TWITCH = 'twitch', 'Twitch'
        YOUTUBE = 'youtube', 'YouTube'
        GRAPH = 'graph', 'Microsoft Graph email'
        TURNSTILE = 'turnstile', 'Cloudflare Turnstile'
        OPENAI = 'openai', 'OpenAI moderation'
        STEAM = 'steam', 'Steam Web API'

    class Source(models.TextChoices):
        ENVIRONMENT = 'environment', 'Server environment'
        DATABASE = 'database', 'Encrypted database record'
        DISABLED = 'disabled', 'Disabled'

    provider = models.CharField(max_length=16, choices=Provider.choices, unique=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.ENVIRONMENT)
    client_id = models.CharField('client ID', max_length=255, blank=True)
    tenant_id = models.CharField('tenant ID', max_length=255, blank=True)
    redirect_uri = models.URLField('callback URL', max_length=500, blank=True)
    site_origin = models.URLField(max_length=255, editable=False)
    encrypted_secret = models.TextField(editable=False, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'provider configuration'
        verbose_name_plural = 'provider configurations'

    def __str__(self):
        return self.get_provider_display()


class ReleaseConfiguration(models.Model):
    """One environment's public access switches, separate from presentation imports."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    construction = models.BooleanField(default=True, help_text="Show the construction page on public routes. Admin and health access remain available.")
    registration = models.BooleanField(default=False, help_text="Allow new accounts. Existing accounts can still sign in when this is off.")
    workshop_submissions = models.BooleanField(default=False, help_text="Allow new Workshop mod requests. Published rulings remain available.")
    rr1_submissions = models.BooleanField("RR1 claims and updates", default=False, help_text="Allow claims and updates for Rat Race 1.0.")
    rr2 = models.BooleanField("RR2 enabled", default=False, help_text="Open Rat Race 2.0 pages and actions. Enable only after its separate acceptance checks.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "release controls"
        verbose_name_plural = "release controls"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="release_configuration_singleton")]

    def __str__(self):
        return "Release controls"
