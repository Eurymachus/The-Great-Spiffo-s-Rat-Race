from django.core.exceptions import ValidationError
from django.db import models


class CatalogueEntry(models.Model):
    class Kind(models.TextChoices):
        SKILL = "skill", "Skill"
        TRAIT = "trait", "Trait"
        ITEM = "item", "Item"
        RECIPE = "recipe", "Recipe"
        TOWN = "town", "Town"
        LOCATION = "location", "Location"
        OUTPOST = "outpost", "Outpost"
        DELIVERABLE = "deliverable", "Deliverable"
        MOD = "mod", "Mod"

    kind = models.CharField(max_length=24, choices=Kind.choices)
    stable_id = models.CharField(
        max_length=255,
        help_text="The exact stable identifier exported by Project Zomboid or TGSRR.",
    )
    display_name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True)
    introduced_in = models.CharField(
        max_length=32,
        blank=True,
        help_text="First supported game version, for example 42.19.",
    )
    removed_in = models.CharField(
        max_length=32,
        blank=True,
        help_text="First game version where this mapping no longer applies.",
    )
    icon_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional static icon key or asset identifier.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("kind", "display_name", "stable_id")
        constraints = (
            models.UniqueConstraint(
                fields=("kind", "stable_id", "introduced_in"),
                name="unique_catalogue_entry_version_start",
            ),
        )
        verbose_name = "catalogue entry"
        verbose_name_plural = "catalogue entries"

    def clean(self):
        if (
            self.introduced_in
            and self.removed_in
            and version_key(self.removed_in) <= version_key(self.introduced_in)
        ):
            raise ValidationError(
                {"removed_in": "The removed version must be later than the introduced version."}
            )

    def __str__(self):
        return f"{self.display_name} ({self.stable_id})"


class CatalogueAlias(models.Model):
    entry = models.ForeignKey(
        CatalogueEntry, on_delete=models.CASCADE, related_name="aliases"
    )
    stable_id = models.CharField(
        max_length=255,
        help_text="A legacy or alternate identifier that resolves to this entry.",
    )
    introduced_in = models.CharField(max_length=32, blank=True)
    removed_in = models.CharField(max_length=32, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("stable_id",)
        constraints = (
            models.UniqueConstraint(
                fields=("stable_id", "introduced_in"),
                name="unique_catalogue_alias_version_start",
            ),
        )
        verbose_name = "catalogue alias"
        verbose_name_plural = "catalogue aliases"

    def clean(self):
        if (
            self.introduced_in
            and self.removed_in
            and version_key(self.removed_in) <= version_key(self.introduced_in)
        ):
            raise ValidationError(
                {"removed_in": "The removed version must be later than the introduced version."}
            )

    def __str__(self):
        return self.stable_id


def version_key(value):
    parts = []
    for part in str(value or "").split("."):
        digits = "".join(character for character in part if character.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)
