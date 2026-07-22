from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from branding.models import ManagedImage


class Page(models.Model):
    class ContentWidth(models.TextChoices):
        NARROW = "narrow", "Narrow - focused reading"
        STANDARD = "standard", "Standard - general content"
        WIDE = "wide", "Wide - dashboards and richer layouts"
        FULL = "full", "Full - use the available page width"

    title = models.CharField(
        max_length=120,
        help_text="An internal name used in administration.",
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        editable=False,
        help_text="A stable internal identifier retained for legacy links.",
    )
    public_path = models.CharField(
        "public address",
        max_length=240,
        unique=True,
        blank=True,
        help_text="A root or nested address such as 'gallery' or 'media/gallery'.",
    )
    is_published = models.BooleanField(
        default=True,
        help_text="Only published pages can be shown publicly.",
    )
    content_width = models.CharField(
        max_length=16,
        choices=ContentWidth.choices,
        default=ContentWidth.STANDARD,
        help_text="The default maximum width used by sections on this page.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        self.public_path = self.public_path.strip().strip("/").lower()
        if self.slug == "home":
            if self.public_path:
                raise ValidationError({"public_path": "The homepage always uses the site root."})
            return
        if not self.public_path:
            raise ValidationError({"public_path": "Enter a public address for this page."})
        segments = self.public_path.split("/")
        if any(not segment or slugify(segment) != segment for segment in segments):
            raise ValidationError({"public_path": "Use lowercase letters, numbers and hyphens separated by single slashes."})
        reserved = {
            "account", "admin", "login", "logout", "pages", "password-change",
            "password-reset", "privacy", "resend", "signup", "thanks", "verify",
        }
        if segments[0] in reserved:
            raise ValidationError({"public_path": f"'{segments[0]}' is reserved for website functionality."})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:110] or "page"
            candidate = base
            suffix = 2
            while Page.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base[:110 - len(str(suffix))]}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.slug == "home":
            return reverse("registry:home")
        return reverse("registry:page", kwargs={"page_path": self.public_path})


class NavigationItem(models.Model):
    label = models.CharField(max_length=80)
    page = models.ForeignKey(
        Page, on_delete=models.CASCADE, related_name="navigation_items",
        blank=True, null=True,
        help_text="Optional. Leave empty to create a non-clickable menu heading.",
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children",
        blank=True, null=True,
    )
    position = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ("parent_id", "position", "label")

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        ancestor = self.parent
        depth = 1
        seen = {self.pk} if self.pk else set()
        while ancestor:
            if ancestor.pk in seen:
                raise ValidationError({"parent": "Navigation items cannot contain themselves."})
            seen.add(ancestor.pk)
            depth += 1
            if depth > 3:
                raise ValidationError({"parent": "Navigation supports at most three visible levels."})
            ancestor = ancestor.parent


class PageSection(models.Model):
    class Width(models.TextChoices):
        INHERIT = "inherit", "Use page width"
        NARROW = "narrow", "Narrow"
        STANDARD = "standard", "Standard"
        WIDE = "wide", "Wide"
        FULL = "full", "Full width"

    class Layout(models.TextChoices):
        SINGLE = "single", "Single column"
        TWO = "two", "Two equal columns"
        WIDE_LEFT = "wide_left", "Two columns - wide left"
        WIDE_RIGHT = "wide_right", "Two columns - wide right"
        THREE = "three", "Three columns"
        FOUR = "four", "Four columns"

    class Background(models.TextChoices):
        DEFAULT = "default", "Page background"
        SURFACE = "surface", "Raised surface"
        ALTERNATE = "alternate", "Alternate surface"

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="sections")
    position = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=120, default="Section")
    is_visible = models.BooleanField(default=True)
    width = models.CharField(max_length=16, choices=Width.choices, default=Width.INHERIT)
    layout = models.CharField(max_length=16, choices=Layout.choices, default=Layout.SINGLE)
    background = models.CharField(
        max_length=16, choices=Background.choices, default=Background.DEFAULT
    )
    full_bleed_background = models.BooleanField(
        default=False,
        help_text="Extend the section background to the viewport edges while keeping content constrained.",
    )

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "page section"
        verbose_name_plural = "page sections"

    def __str__(self):
        return f"{self.page}: {self.name}"


class PageBlock(models.Model):
    class BlockType(models.TextChoices):
        TEXT = "text", "Text"
        ACTION = "action", "Button or link"
        CARD_GROUP = "card_group", "Card group"
        IMAGE = "image", "Image"
        GALLERY = "gallery", "Gallery"

    class TextRole(models.TextChoices):
        EYEBROW = "eyebrow", "Eyebrow"
        HEADING = "heading", "Heading"
        SUBHEADING = "subheading", "Subheading"
        PARAGRAPH = "paragraph", "Paragraph"

    class TextFont(models.TextChoices):
        THEME = "theme", "Theme default"
        DISPLAY = "display", "Theme display font"
        HEADING = "heading", "Theme heading font"
        BODY = "body", "Theme body font"

    class TextSize(models.TextChoices):
        SMALL = "small", "Small"
        STANDARD = "standard", "Standard"
        LARGE = "large", "Large"
        EXTRA_LARGE = "extra_large", "Extra large"

    class TextWeight(models.TextChoices):
        THEME = "theme", "Theme default"
        REGULAR = "regular", "Regular"
        BOLD = "bold", "Bold"

    class ImageFit(models.TextChoices):
        COVER = "cover", "Crop to fill"
        CONTAIN = "contain", "Show whole image"

    class ImageHeight(models.TextChoices):
        STANDARD = "standard", "Standard - maximum 24rem"
        NATURAL = "natural", "Natural proportions"
        SHORT = "short", "Short banner - 12rem"
        TALL = "tall", "Tall banner - 32rem"
        CUSTOM = "custom", "Custom height"

    class ImagePosition(models.TextChoices):
        TOP_LEFT = "left top", "Top left"
        TOP_CENTRE = "center top", "Top centre"
        TOP_RIGHT = "right top", "Top right"
        CENTRE_LEFT = "left center", "Centre left"
        CENTRE = "center center", "Centre"
        CENTRE_RIGHT = "right center", "Centre right"
        BOTTOM_LEFT = "left bottom", "Bottom left"
        BOTTOM_CENTRE = "center bottom", "Bottom centre"
        BOTTOM_RIGHT = "right bottom", "Bottom right"

    class CardColumns(models.TextChoices):
        AUTO = "auto", "Automatic wrapping"
        ONE = "1", "1 card per row"
        TWO = "2", "2 cards per row"
        THREE = "3", "3 cards per row"
        FOUR = "4", "4 cards per row"

    class Audience(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        VISITORS = "visitors", "Signed-out visitors"
        SIGNED_IN = "signed_in", "Signed-in participants"

    class Alignment(models.TextChoices):
        LEFT = "left", "Left"
        CENTRE = "centre", "Centre"
        RIGHT = "right", "Right"

    class Destination(models.TextChoices):
        NONE = "none", "No destination"
        REGISTER = "register", "Sign Up page"
        LOGIN = "login", "Sign In page"
        ACCOUNT = "account", "Participant account"

    class Style(models.TextChoices):
        DEFAULT = "default", "Standard"
        PRIMARY = "primary", "Primary button"
        SECONDARY = "secondary", "Secondary button"
        LINK = "link", "Text link"

    section = models.ForeignKey(PageSection, on_delete=models.CASCADE, related_name="blocks")
    position = models.PositiveSmallIntegerField(default=0)
    column = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    block_type = models.CharField(max_length=24, choices=BlockType.choices)
    content = models.TextField(max_length=2000, blank=True)
    text_role = models.CharField(max_length=12, choices=TextRole.choices, default=TextRole.PARAGRAPH)
    text_font = models.CharField(max_length=8, choices=TextFont.choices, default=TextFont.THEME)
    text_size = models.CharField(max_length=12, choices=TextSize.choices, default=TextSize.STANDARD)
    text_weight = models.CharField(max_length=8, choices=TextWeight.choices, default=TextWeight.THEME)
    audience = models.CharField(max_length=16, choices=Audience.choices, default=Audience.EVERYONE)
    alignment = models.CharField(max_length=8, choices=Alignment.choices, default=Alignment.LEFT)
    destination = models.CharField(max_length=16, choices=Destination.choices, default=Destination.NONE)
    style = models.CharField(max_length=16, choices=Style.choices, default=Style.DEFAULT)
    card_columns = models.CharField(
        "cards per row", max_length=8, choices=CardColumns.choices, default=CardColumns.AUTO,
    )
    image_asset = models.ForeignKey(
        ManagedImage, null=True, blank=True, on_delete=models.PROTECT,
        related_name="page_blocks", verbose_name="image",
    )
    image_alt = models.CharField("alternative text", max_length=200, blank=True)
    image_fit = models.CharField(max_length=12, choices=ImageFit.choices, default=ImageFit.COVER)
    image_height = models.CharField(max_length=12, choices=ImageHeight.choices, default=ImageHeight.STANDARD)
    image_custom_height = models.PositiveSmallIntegerField(
        "custom height (rem)", default=24,
        validators=(MinValueValidator(6), MaxValueValidator(60)),
    )
    image_position = models.CharField(max_length=20, choices=ImagePosition.choices, default=ImagePosition.CENTRE)
    gallery_auto_scroll = models.BooleanField("scroll automatically", default=False)
    gallery_scroll_speed = models.PositiveSmallIntegerField(
        "scroll interval (seconds)", default=5,
        validators=(MinValueValidator(2), MaxValueValidator(30)),
    )
    gallery_loop = models.BooleanField("loop continuously", default=True)
    gallery_show_controls = models.BooleanField("show navigation controls", default=True)
    gallery_show_captions = models.BooleanField("show captions", default=True)
    gallery_expandable = models.BooleanField("allow expanded view", default=True)

    class Meta:
        ordering = ("column", "position", "pk")
        verbose_name = "content block"
        verbose_name_plural = "content blocks"

    def clean(self):
        if self.block_type == self.BlockType.IMAGE and not self.image_asset_id:
            raise ValidationError({"image_asset": "Choose an image."})
        if self.block_type not in (self.BlockType.CARD_GROUP, self.BlockType.IMAGE, self.BlockType.GALLERY) and not self.content.strip():
            raise ValidationError({"content": "This block needs content."})
        if self.column > 3:
            raise ValidationError({"column": "A block must be in columns 1 to 4."})

    def __str__(self):
        return self.content[:80] or self.get_block_type_display()


class SectionItem(models.Model):
    block = models.ForeignKey(
        PageBlock, on_delete=models.CASCADE, related_name="items"
    )
    position = models.PositiveSmallIntegerField(default=0)
    heading = models.CharField(max_length=120)
    description = models.TextField(max_length=500, blank=True)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "card"
        verbose_name_plural = "cards"

    def __str__(self):
        return self.heading


class PageGalleryImage(models.Model):
    block = models.ForeignKey(PageBlock, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.ForeignKey(ManagedImage, on_delete=models.PROTECT, related_name="page_galleries")
    position = models.PositiveSmallIntegerField(default=0)
    alternative_text = models.CharField(max_length=200, blank=True)
    caption = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("position", "pk")
        constraints = (
            models.UniqueConstraint(fields=("block", "image"), name="unique_image_per_page_gallery"),
        )

    def __str__(self):
        return self.caption or self.image.name
