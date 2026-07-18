from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.utils import OperationalError, ProgrammingError


class WebsiteSettings(models.Model):
    SINGLETON_PK = 1
    DEFAULT_MAXIMUM_IMAGE_UPLOAD_SIZE_MB = 5

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
