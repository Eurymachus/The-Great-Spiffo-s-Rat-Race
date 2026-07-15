from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.utils import OperationalError, ProgrammingError


hex_colour = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a six-digit hexadecimal colour such as #F2A33A.",
)


class WebsiteTheme(models.Model):
    class ColourScheme(models.TextChoices):
        DARK = "dark", "Dark"
        LIGHT = "light", "Light"

    class HeadingFont(models.TextChoices):
        SYSTEM = "system", "Modern system"
        CONDENSED = "condensed", "Condensed poster"
        SLAB = "slab", "Slab serif"
        OSWALD = "oswald", "Oswald"
        DERELICT = "derelict", "Derelict"
        DERELICT_ROUGH = "derelict_rough", "Derelict Rough"

    class BodyFont(models.TextChoices):
        SYSTEM = "system", "Modern system"
        HUMANIST = "humanist", "Humanist"
        MONO = "mono", "Technical monospace"
        OSWALD = "oswald", "Oswald"

    class CornerStyle(models.TextChoices):
        SQUARE = "square", "Square"
        SUBTLE = "subtle", "Subtle"
        ROUNDED = "rounded", "Rounded"

    class ShadowStyle(models.TextChoices):
        NONE = "none", "None"
        SOFT = "soft", "Soft"
        DRAMATIC = "dramatic", "Dramatic"

    class BackgroundStyle(models.TextChoices):
        FLAT = "flat", "Flat"
        RADIAL = "radial", "Atmospheric radial"
        ROAD = "road", "Road stripes"

    HEADING_FONT_STACKS = {
        HeadingFont.SYSTEM: "Inter, ui-sans-serif, system-ui, sans-serif",
        HeadingFont.CONDENSED: "Impact, Haettenschweiler, Arial, sans-serif",
        HeadingFont.SLAB: "Rockwell, Georgia, serif",
        HeadingFont.OSWALD: "RatRaceOswald, Impact, sans-serif",
        HeadingFont.DERELICT: "RatRaceDerelict, Impact, sans-serif",
        HeadingFont.DERELICT_ROUGH: "RatRaceDerelictRough, RatRaceDerelict, Impact, sans-serif",
    }
    BODY_FONT_STACKS = {
        BodyFont.SYSTEM: "Inter, ui-sans-serif, system-ui, sans-serif",
        BodyFont.HUMANIST: "Verdana, Tahoma, sans-serif",
        BodyFont.MONO: "Consolas, Monaco, monospace",
        BodyFont.OSWALD: "RatRaceOswald, Arial, sans-serif",
    }
    CORNER_RADII = {
        CornerStyle.SQUARE: "0rem",
        CornerStyle.SUBTLE: "0.45rem",
        CornerStyle.ROUNDED: "1rem",
    }
    SHADOWS = {
        ShadowStyle.NONE: "none",
        ShadowStyle.SOFT: "0 1rem 2.5rem rgba(0, 0, 0, 0.24)",
        ShadowStyle.DRAMATIC: "0 1.5rem 4rem rgba(0, 0, 0, 0.42)",
    }

    name = models.CharField(max_length=80, unique=True)
    preset_key = models.CharField(max_length=40, blank=True, editable=False)
    colour_scheme = models.CharField(
        max_length=8, choices=ColourScheme.choices, default=ColourScheme.DARK
    )
    background_style = models.CharField(
        max_length=12, choices=BackgroundStyle.choices, default=BackgroundStyle.RADIAL
    )
    heading_font = models.CharField(
        max_length=20, choices=HeadingFont.choices, default=HeadingFont.SYSTEM
    )
    body_font = models.CharField(
        max_length=20, choices=BodyFont.choices, default=BodyFont.SYSTEM
    )
    corner_style = models.CharField(
        max_length=12, choices=CornerStyle.choices, default=CornerStyle.ROUNDED
    )
    shadow_style = models.CharField(
        max_length=12, choices=ShadowStyle.choices, default=ShadowStyle.DRAMATIC
    )
    background_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#151912"
    )
    background_highlight_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#394628"
    )
    surface_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#191F15"
    )
    surface_alt_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#0F130D"
    )
    text_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#F6F2DF"
    )
    muted_text_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#C8CDBD"
    )
    accent_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#F2A33A"
    )
    accent_hover_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#F4AD53"
    )
    accent_text_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#17120A"
    )
    border_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#586746"
    )
    success_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#A6D66D"
    )
    error_colour = models.CharField(
        max_length=7, validators=(hex_colour,), default="#FF9B91"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    @property
    def heading_font_stack(self):
        return self.HEADING_FONT_STACKS[self.heading_font]

    @property
    def body_font_stack(self):
        return self.BODY_FONT_STACKS[self.body_font]

    @property
    def corner_radius(self):
        return self.CORNER_RADII[self.corner_style]

    @property
    def box_shadow(self):
        return self.SHADOWS[self.shadow_style]

    def __str__(self):
        return self.name


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
    active_theme = models.ForeignKey(
        WebsiteTheme,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_branding_records",
    )
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
