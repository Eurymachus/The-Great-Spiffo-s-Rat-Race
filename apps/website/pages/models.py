from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

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
        help_text="The page address. The homepage uses 'home'.",
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
    navigation_label = models.CharField(
        max_length=80,
        blank=True,
        help_text="Optional shorter wording for navigation menus.",
    )
    show_in_navigation = models.BooleanField(
        default=False,
        help_text="Make this page eligible for the public navigation menu.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


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
        SMALL_HEADING = "small_heading", "Small heading"
        HEADING = "heading", "Heading"
        TEXT = "text", "Text"
        ACTION = "action", "Button or link"
        CARD_GROUP = "card_group", "Card group"
        IMAGE = "image", "Image"
        GALLERY = "gallery", "Gallery"

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

    class Destination(models.TextChoices):
        NONE = "none", "No destination"
        REGISTER = "register", "Sign-up page"
        LOGIN = "login", "Login page"
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
    audience = models.CharField(max_length=16, choices=Audience.choices, default=Audience.EVERYONE)
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
