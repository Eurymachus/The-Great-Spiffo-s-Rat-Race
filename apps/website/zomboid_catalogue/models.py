from django.core.exceptions import ValidationError
from django.db import models


class CatalogueEntry(models.Model):
    class Kind(models.TextChoices):
        SKILL = "skill", "Skill"
        TRAIT = "trait", "Trait"
        OCCUPATION = "occupation", "Occupation"
        ITEM = "item", "Item"
        RECIPE = "recipe", "Recipe"
        TOWN = "town", "Town"
        LOCATION = "location", "Location"
        ANIMAL = "animal", "Animal"
        OUTPOST = "outpost", "Outpost"
        DELIVERABLE = "deliverable", "Deliverable"
        MOD = "mod", "Mod"

    kind = models.CharField(max_length=24, choices=Kind.choices)
    stable_id = models.CharField(
        max_length=255,
        help_text="The exact stable identifier exported by Project Zomboid or TGSRR.",
    )
    display_name = models.CharField(max_length=255)
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


class TraitDetails(models.Model):
    entry = models.OneToOneField(
        CatalogueEntry, on_delete=models.CASCADE, related_name="trait_details"
    )
    point_cost = models.SmallIntegerField(default=0)
    description = models.TextField(blank=True)
    is_profession_trait = models.BooleanField(default=False)
    disabled_in_multiplayer = models.BooleanField(default=False)
    xp_boosts = models.JSONField(default=dict, blank=True)
    mutually_exclusive_traits = models.JSONField(default=list, blank=True)
    granted_recipes = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "trait details"
        verbose_name_plural = "trait details"

    def __str__(self):
        return self.entry.display_name


class OccupationDetails(models.Model):
    entry = models.OneToOneField(
        CatalogueEntry, on_delete=models.CASCADE, related_name="occupation_details"
    )
    point_cost = models.SmallIntegerField(default=0)
    description = models.TextField(blank=True)
    granted_traits = models.JSONField(default=list, blank=True)
    xp_boosts = models.JSONField(default=dict, blank=True)
    granted_recipes = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "occupation details"
        verbose_name_plural = "occupation details"

    def __str__(self):
        return self.entry.display_name


class SkillDetails(models.Model):
    entry = models.OneToOneField(
        CatalogueEntry, on_delete=models.CASCADE, related_name="skill_details"
    )
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=120,
        blank=True,
        help_text="The Project Zomboid skill category identifier.",
    )
    level_xp = models.JSONField(default=list, blank=True)
    is_passive = models.BooleanField(default=False)

    class Meta:
        verbose_name = "skill details"
        verbose_name_plural = "skill details"

    def __str__(self):
        return self.entry.display_name


class ItemDisplayCategory(models.Model):
    stable_id = models.CharField(
        max_length=120,
        unique=True,
        help_text="The exact Project Zomboid DisplayCategory identifier.",
    )
    display_name = models.CharField(max_length=120)

    class Meta:
        ordering = ("display_name", "stable_id")
        verbose_name = "item display category"
        verbose_name_plural = "item display categories"

    def __str__(self):
        return self.display_name


class ItemDetails(models.Model):
    entry = models.OneToOneField(
        CatalogueEntry, on_delete=models.CASCADE, related_name="item_details"
    )
    pz_item_type = models.CharField(
        max_length=120,
        blank=True,
        help_text="The exact Project Zomboid ItemType value.",
    )
    display_category = models.ForeignKey(
        ItemDisplayCategory,
        on_delete=models.PROTECT,
        related_name="items",
        null=True,
        blank=True,
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Exact Project Zomboid item tags.",
    )
    capabilities = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Deterministic capabilities derived from Project Zomboid fields, "
            "such as weapon, tool, literature, book, or magazine."
        ),
    )
    weapon_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Exact Project Zomboid weapon category identifiers.",
    )
    weapon_skill = models.ForeignKey(
        SkillDetails,
        on_delete=models.PROTECT,
        related_name="weapon_items",
        null=True,
        blank=True,
        help_text="Skill deterministically resolved from Project Zomboid weapon evidence.",
    )
    weight = models.FloatField(null=True, blank=True)
    raw_properties = models.JSONField(
        default=dict,
        blank=True,
        help_text="The complete parsed Project Zomboid item definition.",
    )

    class Meta:
        verbose_name = "item details"
        verbose_name_plural = "item details"

    def __str__(self):
        return f"{self.entry.display_name}: {', '.join(self.capabilities)}"


class AnimalDetails(models.Model):
    class LifeStage(models.TextChoices):
        BABY = "baby", "Baby"
        JUVENILE = "juvenile", "Juvenile"
        ADULT = "adult", "Adult"

    entry = models.OneToOneField(
        CatalogueEntry, on_delete=models.CASCADE, related_name="animal_details"
    )
    species_id = models.CharField(
        max_length=120,
        help_text="Website-owned stable species identifier used for grouping.",
    )
    species_name = models.CharField(max_length=120)
    category = models.CharField(
        max_length=120,
        blank=True,
        help_text="Website-owned animal grouping, such as Mammal or Bird.",
    )
    life_stage = models.CharField(
        max_length=16, choices=LifeStage.choices, blank=True
    )

    class Meta:
        ordering = ("species_name", "life_stage", "entry__display_name")
        verbose_name = "animal details"
        verbose_name_plural = "animal details"

    def __str__(self):
        return f"{self.entry.display_name}: {self.species_name}"


class DeliverableDetails(models.Model):
    entry = models.OneToOneField(
        CatalogueEntry, on_delete=models.CASCADE, related_name="deliverable_details"
    )
    category = models.CharField(
        max_length=120,
        blank=True,
        help_text="Rat Race grouping for this deliverable or objective.",
    )

    class Meta:
        verbose_name = "deliverable details"
        verbose_name_plural = "deliverable details"

    def __str__(self):
        return f"{self.entry.display_name}: {self.category}"


class MapLocationVersion(models.Model):
    class LocationType(models.TextChoices):
        OUTPOST = "outpost", "Outpost"
        LANDMARK = "landmark", "Landmark"
        START_AREA = "start_area", "Starting area"
        TOWN = "town", "Town"

    entry = models.ForeignKey(
        CatalogueEntry, on_delete=models.CASCADE, related_name="map_versions"
    )
    location_type = models.CharField(max_length=16, choices=LocationType.choices)
    game_version = models.CharField(max_length=32)
    registry_version = models.PositiveIntegerField(default=1)
    anchor_x = models.IntegerField()
    anchor_y = models.IntegerField()
    anchor_z = models.IntegerField(default=0)
    min_x = models.IntegerField(null=True, blank=True)
    min_y = models.IntegerField(null=True, blank=True)
    max_x = models.IntegerField(null=True, blank=True)
    max_y = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ("location_type", "entry__display_name", "game_version")
        constraints = (
            models.UniqueConstraint(
                fields=("entry", "game_version", "registry_version"),
                name="unique_map_location_version",
            ),
        )

    def clean(self):
        bounds = (self.min_x, self.min_y, self.max_x, self.max_y)
        if any(value is not None for value in bounds) and any(
            value is None for value in bounds
        ):
            raise ValidationError("Map bounds must be entirely present or absent.")
        if self.min_x is not None and (
            self.min_x > self.max_x or self.min_y > self.max_y
        ):
            raise ValidationError("Map bounds cannot be inverted.")

    def __str__(self):
        return f"{self.entry.display_name}, {self.game_version} registry {self.registry_version}"


class MapLocationBuilding(models.Model):
    location_version = models.ForeignKey(
        MapLocationVersion, on_delete=models.CASCADE, related_name="buildings"
    )
    building_id = models.CharField(
        max_length=160,
        help_text="The raw BuildingDef ID observed in this exact game/map version.",
    )

    class Meta:
        ordering = ("building_id",)
        constraints = (
            models.UniqueConstraint(
                fields=("location_version", "building_id"),
                name="unique_map_location_building",
            ),
        )

    def __str__(self):
        return f"{self.location_version}: {self.building_id}"


def catalogue_asset_upload_to(instance, filename):
    version = instance.entry.introduced_in or "unversioned"
    return f"catalogue/{version}/{instance.entry.kind}/{filename}"


class CatalogueAsset(models.Model):
    class Role(models.TextChoices):
        ICON = "icon", "Icon"
        SCREENSHOT = "screenshot", "Screenshot"
        ILLUSTRATION = "illustration", "Illustration"

    class Availability(models.TextChoices):
        IMPORTED = "imported", "Imported"
        PACKED = "packed", "Packed in game texture archive"
        MISSING = "missing", "Not found"

    class SourceType(models.TextChoices):
        UNKNOWN = "unknown", "No served image"
        GAME = "game", "Project Zomboid"
        PZWIKI = "pzwiki", "PZwiki"
        MANUAL = "manual", "Manual override"

    class GameAvailability(models.TextChoices):
        UNKNOWN = "unknown", "Not checked"
        UNPACKED = "unpacked", "Unpacked file available"
        PACKED = "packed", "Packed texture reference only"
        MISSING = "missing", "Not found"

    entry = models.ForeignKey(
        CatalogueEntry, on_delete=models.CASCADE, related_name="assets"
    )
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.ICON)
    source_key = models.CharField(
        max_length=255,
        help_text="Project Zomboid texture key or other deterministic source identifier.",
    )
    source_path = models.CharField(max_length=500, blank=True)
    source_checksum = models.CharField(max_length=64, blank=True)
    source_type = models.CharField(
        max_length=16,
        choices=SourceType.choices,
        default=SourceType.UNKNOWN,
        help_text="Provenance of the image currently served by the website.",
    )
    game_availability = models.CharField(
        max_length=16,
        choices=GameAvailability.choices,
        default=GameAvailability.UNKNOWN,
        help_text="Whether Project Zomboid exposes an accessible file or only a packed reference.",
    )
    game_source_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="The authoritative loose Project Zomboid file path when available.",
    )
    game_source_checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text="Checksum of the authoritative loose Project Zomboid file when available.",
    )
    file = models.ImageField(upload_to=catalogue_asset_upload_to, blank=True)
    availability = models.CharField(
        max_length=16, choices=Availability.choices, default=Availability.MISSING
    )
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "role", "source_key")
        constraints = (
            models.UniqueConstraint(
                fields=("entry", "role", "source_key"),
                name="unique_catalogue_asset_source",
            ),
        )

    def __str__(self):
        return f"{self.entry.display_name}: {self.get_role_display()}"


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
