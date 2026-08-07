from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from branding.models import ManagedImage


class CodeManagedPage(models.Model):
    class Audience(models.TextChoices):
        PUBLIC = "public", "Public"
        PARTICIPANT = "participant", "Signed-in participant"
        STAFF = "staff", "Staff"

    class Availability(models.TextChoices):
        AVAILABLE = "available", "Available"
        PLANNED = "planned", "Planned"
        DISABLED = "disabled", "Disabled"

    key = models.SlugField(
        max_length=80,
        unique=True,
        editable=False,
        help_text="Stable identity owned by version-controlled website code.",
    )
    title = models.CharField(max_length=120, editable=False)
    description = models.TextField(max_length=500, editable=False)
    audience = models.CharField(
        max_length=16, choices=Audience.choices, editable=False
    )
    availability = models.CharField(
        max_length=16, choices=Availability.choices, editable=False
    )
    route_name = models.CharField(max_length=160, blank=True, editable=False)
    address = models.CharField(max_length=240, editable=False)

    class Meta:
        ordering = ("title",)
        verbose_name = "code-managed page"
        verbose_name_plural = "code-managed pages"

    def __str__(self):
        return self.title

    @property
    def is_navigation_target(self):
        return (
            self.availability == self.Availability.AVAILABLE
            and bool(self.route_name)
        )

    def get_absolute_url(self):
        if not self.is_navigation_target:
            return ""
        return reverse(self.route_name)

    def is_visible_to(self, user):
        if self.audience == self.Audience.PUBLIC:
            return True
        if self.audience == self.Audience.PARTICIPANT:
            return user.is_authenticated
        return user.is_authenticated and user.is_staff


class Page(models.Model):
    class Audience(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        VISITORS = "visitors", "Signed-out visitors"
        SIGNED_IN = "signed_in", "Signed-in participants"
        STAFF = "staff", "Staff"

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
    audience = models.CharField(
        max_length=16,
        choices=Audience.choices,
        default=Audience.EVERYONE,
        help_text="Choose who can open this page directly or see it in navigation.",
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

    def is_visible_to(self, user):
        if self.audience == self.Audience.VISITORS:
            return not user.is_authenticated
        if self.audience == self.Audience.SIGNED_IN:
            return user.is_authenticated
        if self.audience == self.Audience.STAFF:
            return user.is_authenticated and user.is_staff
        return True


class NavigationItem(models.Model):
    class Audience(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        VISITORS = "visitors", "Signed-out visitors"
        SIGNED_IN = "signed_in", "Signed-in participants"
        STAFF = "staff", "Staff"

    label = models.CharField(max_length=80)
    page = models.ForeignKey(
        Page, on_delete=models.CASCADE, related_name="navigation_items",
        blank=True, null=True,
        help_text="Optional. Leave empty to create a non-clickable menu heading.",
    )
    code_page = models.ForeignKey(
        CodeManagedPage,
        on_delete=models.PROTECT,
        related_name="navigation_items",
        blank=True,
        null=True,
        help_text="Optional code-managed application destination.",
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children",
        blank=True, null=True,
    )
    position = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    audience = models.CharField(
        max_length=16,
        choices=Audience.choices,
        default=Audience.EVERYONE,
        help_text="Choose who can see this navigation item and its nested branch.",
    )

    class Meta:
        ordering = ("parent_id", "position", "label")
        constraints = (
            models.CheckConstraint(
                condition=~(models.Q(page__isnull=False) & models.Q(code_page__isnull=False)),
                name="navigation_item_has_one_destination",
            ),
        )

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        if self.page_id and self.code_page_id:
            raise ValidationError(
                {"code_page": "Choose either an editorial page or a code-managed page."}
            )
        if self.code_page_id and not self.code_page.is_navigation_target:
            raise ValidationError(
                {"code_page": "Only available fixed routes can be navigation destinations."}
            )
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

    def get_absolute_url(self):
        if self.page_id:
            return self.page.get_absolute_url()
        if self.code_page_id:
            return self.code_page.get_absolute_url()
        return ""

    def is_visible_to(self, user):
        if self.audience == self.Audience.VISITORS:
            return not user.is_authenticated
        if self.audience == self.Audience.SIGNED_IN:
            return user.is_authenticated
        if self.audience == self.Audience.STAFF:
            return user.is_authenticated and user.is_staff
        return True


class PageSection(models.Model):
    class SectionType(models.TextChoices):
        CONTENT = "content", "Content section"
        TABS = "tabs", "Tabbed content"
        SEPARATOR = "separator", "Separator"

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
        ALTERNATE_FULL = "alternate_full", "Alternate surface - full width"

    class VerticalPadding(models.TextChoices):
        STANDARD = "standard", "Standard"
        COMPACT = "compact", "Compact"
        NONE = "none", "None"

    class SeparatorStyle(models.TextChoices):
        SPACE = "space", "Space only"
        LINE = "line", "Subtle line"
        ACCENT = "accent", "Accent line"

    class SeparatorSpacing(models.TextChoices):
        VERY_SMALL = "very_small", "Very small"
        SMALL = "small", "Small"
        STANDARD = "standard", "Standard"
        LARGE = "large", "Large"

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="sections")
    position = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=120, default="Section")
    is_visible = models.BooleanField(default=True)
    section_type = models.CharField(
        max_length=16, choices=SectionType.choices, default=SectionType.CONTENT
    )
    width = models.CharField(max_length=16, choices=Width.choices, default=Width.INHERIT)
    layout = models.CharField(max_length=16, choices=Layout.choices, default=Layout.SINGLE)
    background = models.CharField(
        max_length=16, choices=Background.choices, default=Background.DEFAULT
    )
    full_bleed_background = models.BooleanField(
        default=False,
        help_text="Extend the section background to the viewport edges while keeping content constrained.",
    )
    vertical_padding = models.CharField(
        max_length=16, choices=VerticalPadding.choices, default=VerticalPadding.STANDARD
    )
    separator_style = models.CharField(
        max_length=16, choices=SeparatorStyle.choices, default=SeparatorStyle.SPACE
    )
    separator_spacing = models.CharField(
        max_length=16, choices=SeparatorSpacing.choices, default=SeparatorSpacing.STANDARD
    )
    tabs_config = models.JSONField(
        "tabs",
        default=list,
        blank=True,
        help_text="Managed labels and descriptions for a tabbed section's column panels.",
    )

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "page section"
        verbose_name_plural = "page sections"

    def __str__(self):
        return f"{self.page}: {self.name}"

    def clean(self):
        super().clean()
        if self.background != self.Background.ALTERNATE:
            self.full_bleed_background = False

    def normalised_tabs(self):
        from django.utils.text import slugify

        column_count = {
            self.Layout.SINGLE: 1,
            self.Layout.TWO: 2,
            self.Layout.WIDE_LEFT: 2,
            self.Layout.WIDE_RIGHT: 2,
            self.Layout.THREE: 3,
            self.Layout.FOUR: 4,
        }.get(self.layout, 1)
        configured = self.tabs_config if isinstance(self.tabs_config, list) else []
        tabs = []
        used_slugs = set()
        default_seen = False
        for index in range(column_count):
            raw = configured[index] if index < len(configured) and isinstance(configured[index], dict) else {}
            label = str(raw.get("label", "")).strip()[:80] or f"Tab {index + 1}"
            base_slug = slugify(label)[:70] or f"tab-{index + 1}"
            slug = base_slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slugs.add(slug)
            is_default = bool(raw.get("is_default")) and not default_seen
            default_seen = default_seen or is_default
            tabs.append({
                "label": label,
                "description": str(raw.get("description", "")).strip()[:200],
                "slug": slug,
                "is_default": is_default,
            })
        if tabs and not default_seen:
            tabs[0]["is_default"] = True
        return tabs


class PageBlock(models.Model):
    class BlockType(models.TextChoices):
        TEXT = "text", "Text"
        ACTION = "action", "Button or link"
        CARD_GROUP = "card_group", "Card group"
        SEPARATOR = "separator", "Separator"
        COMMUNITY_STATS = "community_stats", "Community statistics"
        IMAGE = "image", "Image"
        GALLERY = "gallery", "Gallery"
        RANKING_TABLE = "ranking_table", "Ranking table"

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

    class SeparatorStyle(models.TextChoices):
        SPACE = "space", "Space only"
        LINE = "line", "Subtle line"
        ACCENT = "accent", "Accent line"

    class SeparatorSpacing(models.TextChoices):
        VERY_SMALL = "very_small", "Very small"
        SMALL = "small", "Small"
        STANDARD = "standard", "Standard"
        LARGE = "large", "Large"

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
    separator_style = models.CharField(
        max_length=12, choices=SeparatorStyle.choices, default=SeparatorStyle.SPACE,
    )
    separator_spacing = models.CharField(
        max_length=12, choices=SeparatorSpacing.choices, default=SeparatorSpacing.STANDARD,
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
    image_expandable = models.BooleanField("allow expanded view", default=False)
    gallery_auto_scroll = models.BooleanField("scroll automatically", default=False)
    gallery_scroll_speed = models.PositiveSmallIntegerField(
        "scroll interval (seconds)", default=5,
        validators=(MinValueValidator(2), MaxValueValidator(30)),
    )
    gallery_loop = models.BooleanField("loop continuously", default=True)
    gallery_show_controls = models.BooleanField("show navigation controls", default=True)
    gallery_show_captions = models.BooleanField("show captions", default=True)
    gallery_expandable = models.BooleanField("allow expanded view", default=True)
    ranking_config = models.JSONField(
        "ranking table configuration", default=dict, blank=True,
        help_text="Validated filters, result selection, ordering, columns and display controls.",
    )
    community_stats_config = models.JSONField(
        "community statistics configuration", default=dict, blank=True,
        help_text="Validated selection and ordering of verified community metrics.",
    )

    class Meta:
        ordering = ("column", "position", "pk")
        verbose_name = "content block"
        verbose_name_plural = "content blocks"

    def clean(self):
        if self.block_type == self.BlockType.IMAGE and not self.image_asset_id:
            raise ValidationError({"image_asset": "Choose an image."})
        if self.block_type not in (
            self.BlockType.CARD_GROUP, self.BlockType.IMAGE,
            self.BlockType.GALLERY, self.BlockType.RANKING_TABLE,
            self.BlockType.COMMUNITY_STATS, self.BlockType.SEPARATOR,
        ) and not self.content.strip():
            raise ValidationError({"content": "This block needs content."})
        if self.block_type == self.BlockType.RANKING_TABLE:
            from .ranking_config import validate_ranking_config

            try:
                self.ranking_config = validate_ranking_config(self.ranking_config)
            except ValidationError as exc:
                raise ValidationError({"ranking_config": exc.messages}) from exc
        if self.block_type == self.BlockType.COMMUNITY_STATS:
            from .community_stats import validate_community_stats_config

            try:
                self.community_stats_config = validate_community_stats_config(
                    self.community_stats_config
                )
            except ValidationError as exc:
                raise ValidationError(
                    {"community_stats_config": exc.messages}
                ) from exc
        if self.column > 3:
            raise ValidationError({"column": "A block must be in columns 1 to 4."})

    def __str__(self):
        return self.content[:80] or self.get_block_type_display()


class SectionItem(models.Model):
    class CardType(models.TextChoices):
        STANDARD = "standard", "Standard card"
        LINKED = "linked", "Linked action card"

    class Audience(models.TextChoices):
        INHERIT = "inherit", "Inherit from card group"
        EVERYONE = "everyone", "Everyone"
        VISITORS = "visitors", "Signed-out visitors"
        SIGNED_IN = "signed_in", "Signed-in participants"
        HIDDEN = "hidden", "Hidden"

    block = models.ForeignKey(
        PageBlock, on_delete=models.CASCADE, related_name="items"
    )
    card_type = models.CharField(
        max_length=12, choices=CardType.choices, default=CardType.STANDARD,
    )
    position = models.PositiveSmallIntegerField(default=0)
    heading = models.CharField(max_length=120)
    description = models.TextField(max_length=500, blank=True)
    card_label = models.CharField(
        "number or label",
        max_length=16,
        blank=True,
        help_text="Optional text displayed above the card heading, such as 01 or Start.",
    )
    audience = models.CharField(
        max_length=16,
        choices=Audience.choices,
        default=Audience.INHERIT,
    )
    alt_text = models.CharField(
        max_length=160,
        blank=True,
        help_text="Accessible text describing where the linked card leads.",
    )
    destination_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="A site-relative path, page anchor, or secure web address.",
    )

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "card"
        verbose_name_plural = "cards"

    def __str__(self):
        return self.heading

    def clean(self):
        super().clean()
        if (
            self.block_id
            and self.block.block_type == PageBlock.BlockType.CARD_GROUP
            and self.card_type == self.CardType.LINKED
        ):
            if not self.alt_text.strip():
                raise ValidationError({"alt_text": "Enter alt text for the linked card."})
            from .destinations import is_safe_managed_destination

            if not is_safe_managed_destination(self.destination_url):
                raise ValidationError(
                    {"destination_url": "Use a site-relative path or an https address."}
                )


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
