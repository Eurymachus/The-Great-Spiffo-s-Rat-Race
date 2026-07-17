from django.core.exceptions import ValidationError
from django.db import models


class Page(models.Model):
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
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


class PageSection(models.Model):
    class SectionType(models.TextChoices):
        INTRODUCTION = "introduction", "Introduction and actions"
        STEPS = "steps", "Numbered information cards"

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(max_length=24, choices=SectionType.choices)
    position = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
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
