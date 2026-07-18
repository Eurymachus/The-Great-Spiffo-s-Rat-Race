from django.core.exceptions import ValidationError
from django.db import models


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
    class SectionType(models.TextChoices):
        INTRODUCTION = "introduction", "Introduction and actions"
        STEPS = "steps", "Numbered information cards"

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
    section_type = models.CharField(max_length=24, choices=SectionType.choices)
    position = models.PositiveSmallIntegerField(default=0)
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
    small_heading = models.CharField(max_length=160, blank=True)
    main_heading = models.CharField(max_length=240, blank=True)
    introduction = models.TextField(max_length=1000, blank=True)
    visitor_primary_button = models.CharField(max_length=80, blank=True)
    visitor_secondary_link = models.CharField(max_length=80, blank=True)
    signed_in_button = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "page section"
        verbose_name_plural = "page sections"

    def clean(self):
        if self.section_type == self.SectionType.INTRODUCTION and not self.main_heading:
            raise ValidationError(
                {"main_heading": "An introduction section needs a main heading."}
            )

    def __str__(self):
        return f"{self.page}: {self.get_section_type_display()}"


class SectionItem(models.Model):
    section = models.ForeignKey(
        PageSection, on_delete=models.CASCADE, related_name="items"
    )
    position = models.PositiveSmallIntegerField(default=0)
    heading = models.CharField(max_length=120)
    description = models.TextField(max_length=500, blank=True)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "section item"
        verbose_name_plural = "section items"

    def __str__(self):
        return self.heading
