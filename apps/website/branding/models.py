from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db.utils import OperationalError, ProgrammingError


hex_colour = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a six-digit hexadecimal colour such as #F2A33A.",
)


def validate_brand_image_size(image):
    if image.size > 5 * 1024 * 1024:
        raise ValidationError("Brand images must be 5 MB or smaller.")


brand_image_validators = (
    FileExtensionValidator(("png", "jpg", "jpeg", "webp", "ico")),
    validate_brand_image_size,
)


class WebsiteTheme(models.Model):
    class FontWeight(models.TextChoices):
        EXTRA_LIGHT = "200", "ExtraLight (200)"
        LIGHT = "300", "Light (300)"
        REGULAR = "400", "Regular (400)"
        MEDIUM = "500", "Medium (500)"
        SEMI_BOLD = "600", "SemiBold (600)"
        BOLD = "700", "Bold (700)"

    class FontSpacing(models.TextChoices):
        TIGHT = "tight", "Tight"
        NORMAL = "normal", "Normal"
        RELAXED = "relaxed", "Relaxed"
        WIDE = "wide", "Wide"

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
    FONT_SPACING_VALUES = {
        FontSpacing.TIGHT: "-0.03em",
        FontSpacing.NORMAL: "0em",
        FontSpacing.RELAXED: "0.03em",
        FontSpacing.WIDE: "0.08em",
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
    display_font = models.CharField(
        max_length=20, choices=HeadingFont.choices, default=HeadingFont.SYSTEM
    )
    body_font = models.CharField(
        max_length=20, choices=BodyFont.choices, default=BodyFont.SYSTEM
    )
    heading_font_weight = models.CharField(
        max_length=3, choices=FontWeight.choices, default=FontWeight.BOLD
    )
    body_font_weight = models.CharField(
        max_length=3, choices=FontWeight.choices, default=FontWeight.REGULAR
    )
    heading_font_spacing = models.CharField(
        max_length=8, choices=FontSpacing.choices, default=FontSpacing.NORMAL
    )
    body_font_spacing = models.CharField(
        max_length=8, choices=FontSpacing.choices, default=FontSpacing.NORMAL
    )
    display_font_weight = models.CharField(
        max_length=3, choices=FontWeight.choices, default=FontWeight.BOLD
    )
    display_font_spacing = models.CharField(
        max_length=8, choices=FontSpacing.choices, default=FontSpacing.NORMAL
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
        verbose_name = "theme"
        verbose_name_plural = "themes"

    @property
    def heading_font_stack(self):
        return self.HEADING_FONT_STACKS[self.heading_font]

    @property
    def display_font_stack(self):
        return self.HEADING_FONT_STACKS[self.display_font]

    @property
    def body_font_stack(self):
        return self.BODY_FONT_STACKS[self.body_font]

    @property
    def heading_letter_spacing(self):
        return self.FONT_SPACING_VALUES[self.heading_font_spacing]

    @property
    def display_letter_spacing(self):
        return self.FONT_SPACING_VALUES[self.display_font_spacing]

    @property
    def body_letter_spacing(self):
        return self.FONT_SPACING_VALUES[self.body_font_spacing]

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
    homepage_small_heading = models.CharField(
        "small heading",
        max_length=160,
        default=settings.SITE_HOMEPAGE_SMALL_HEADING,
    )
    homepage_main_heading = models.CharField(
        "main heading",
        max_length=240,
        default=settings.SITE_HOMEPAGE_MAIN_HEADING,
    )
    homepage_introduction = models.TextField(
        "introduction text",
        max_length=600,
        default=settings.SITE_HOMEPAGE_INTRODUCTION,
    )
    homepage_primary_button = models.CharField(
        "primary button text",
        max_length=80,
        default=settings.SITE_HOMEPAGE_PRIMARY_BUTTON,
    )
    homepage_secondary_link = models.CharField(
        "secondary link text",
        max_length=80,
        default=settings.SITE_HOMEPAGE_SECONDARY_LINK,
    )
    homepage_account_button = models.CharField(
        "signed-in account button text",
        max_length=80,
        default=settings.SITE_HOMEPAGE_ACCOUNT_BUTTON,
    )
    join_step_1_heading = models.CharField(
        "step 1 heading",
        max_length=100,
        default=settings.SITE_JOIN_STEP_1_HEADING,
    )
    join_step_1_description = models.CharField(
        "step 1 description",
        max_length=240,
        default=settings.SITE_JOIN_STEP_1_DESCRIPTION,
    )
    join_step_2_heading = models.CharField(
        "step 2 heading",
        max_length=100,
        default=settings.SITE_JOIN_STEP_2_HEADING,
    )
    join_step_2_description = models.CharField(
        "step 2 description",
        max_length=240,
        default=settings.SITE_JOIN_STEP_2_DESCRIPTION,
    )
    join_step_3_heading = models.CharField(
        "step 3 heading",
        max_length=100,
        default=settings.SITE_JOIN_STEP_3_HEADING,
    )
    join_step_3_description = models.CharField(
        "step 3 description",
        max_length=240,
        default=settings.SITE_JOIN_STEP_3_DESCRIPTION,
    )
    participant_label = models.CharField(
        "participant name",
        max_length=60,
        default=settings.SITE_PARTICIPANT_LABEL,
    )
    participant_plural_label = models.CharField(
        "participant plural",
        max_length=60,
        default=settings.SITE_PARTICIPANT_PLURAL_LABEL,
    )
    former_participant_label = models.CharField(
        max_length=60, default=settings.SITE_FORMER_PARTICIPANT_LABEL
    )
    run_update_label = models.CharField(
        "run update name",
        max_length=60,
        default=settings.SITE_RUN_UPDATE_LABEL,
    )
    run_update_plural_label = models.CharField(
        "run update plural",
        max_length=60,
        default=settings.SITE_RUN_UPDATE_PLURAL_LABEL,
    )
    disclaimer = models.CharField(max_length=240, default=settings.SITE_DISCLAIMER)
    enable_header_logo = models.BooleanField(default=False)
    header_logo = models.ImageField(
        upload_to="branding/",
        blank=True,
        validators=brand_image_validators,
    )
    header_logo_alt = models.CharField(
        "header logo alternative text",
        max_length=160,
        blank=True,
        help_text="Describe the logo for people who cannot see it.",
    )
    enable_favicon = models.BooleanField(default=False)
    favicon = models.ImageField(
        upload_to="branding/",
        blank=True,
        validators=brand_image_validators,
        help_text="A square PNG or ICO works best.",
    )
    enable_social_image = models.BooleanField(default=False)
    social_image = models.ImageField(
        "social sharing image",
        upload_to="branding/",
        blank=True,
        validators=brand_image_validators,
        help_text="Used when the website is shared on services such as Discord.",
    )
    enable_homepage_feature_image = models.BooleanField(default=False)
    homepage_feature_image = models.ImageField(
        upload_to="branding/",
        blank=True,
        validators=brand_image_validators,
    )
    homepage_feature_image_alt = models.CharField(
        "homepage feature image alternative text",
        max_length=200,
        blank=True,
    )
    enable_background_image = models.BooleanField(default=False)
    background_image = models.ImageField(
        upload_to="branding/",
        blank=True,
        validators=brand_image_validators,
        help_text="Decorative only. The active theme colour remains as a fallback.",
    )
    show_attribution = models.BooleanField(default=True)
    attribution_text = models.TextField(
        max_length=600,
        default=settings.SITE_ATTRIBUTION_TEXT,
    )
    attribution_url = models.URLField(default=settings.SITE_ATTRIBUTION_URL)
    attribution_new_tab = models.BooleanField(
        "open attribution link in a new tab",
        default=True,
    )
    active_theme = models.ForeignKey(
        WebsiteTheme,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_branding_records",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "branding"
        verbose_name_plural = "branding"

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
