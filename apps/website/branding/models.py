from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import OperationalError, ProgrammingError


class SiteBranding(models.Model):
    SINGLETON_PK = 1

    id = models.PositiveSmallIntegerField(
        primary_key=True, default=SINGLETON_PK, editable=False
    )
    full_title = models.CharField(max_length=120, default=settings.SITE_FULL_TITLE)
    short_title = models.CharField(max_length=60, default=settings.SITE_SHORT_TITLE)
    tagline = models.CharField(max_length=160, default=settings.SITE_TAGLINE)
    welcome_message = models.CharField(
        max_length=160, default=settings.SITE_WELCOME_MESSAGE
    )
    former_participant_label = models.CharField(
        max_length=60, default=settings.SITE_FORMER_PARTICIPANT_LABEL
    )
    disclaimer = models.CharField(max_length=240, default=settings.SITE_DISCLAIMER)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site branding"
        verbose_name_plural = "site branding"

    @classmethod
    def current(cls):
        try:
            return cls.objects.filter(pk=cls.SINGLETON_PK).first()
        except (OperationalError, ProgrammingError):
            return None

    def clean(self):
        if self.pk not in (None, self.SINGLETON_PK):
            raise ValidationError("Only one site-branding record is allowed.")

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.full_title
