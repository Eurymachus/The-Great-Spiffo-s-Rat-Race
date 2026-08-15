from django.contrib import admin

from .models import (
    AnimalDetails,
    CatalogueAlias,
    CatalogueAsset,
    CatalogueEntry,
    DeliverableDetails,
    ItemDisplayCategory,
    ItemDetails,
    MapLocationBuilding,
    MapLocationVersion,
    OccupationDetails,
    SkillDetails,
    TraitDetails,
)


class CatalogueAliasInline(admin.TabularInline):
    model = CatalogueAlias
    extra = 0
    fields = ("stable_id", "introduced_in", "removed_in", "notes")


class CatalogueAssetInline(admin.TabularInline):
    model = CatalogueAsset
    extra = 0
    fields = (
        "role",
        "source_key",
        "source_type",
        "availability",
        "game_availability",
        "file",
        "alt_text",
        "caption",
        "sort_order",
    )
    readonly_fields = ("availability", "game_availability")


class MapLocationBuildingInline(admin.TabularInline):
    model = MapLocationBuilding
    extra = 0


@admin.register(CatalogueEntry)
class CatalogueEntryAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "kind",
        "stable_id",
        "version_span",
        "is_active",
        "updated_at",
    )
    list_filter = ("kind", "is_active", "introduced_in", "removed_in")
    search_fields = ("display_name", "stable_id", "aliases__stable_id")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("kind", "stable_id", "display_name")}),
        (
            "Game version applicability",
            {"fields": ("introduced_in", "removed_in", "is_active")},
        ),
        ("Presentation", {"fields": ("icon_key",)}),
        ("Catalogue record", {"fields": ("notes", "created_at", "updated_at")}),
    )
    inlines = (CatalogueAliasInline, CatalogueAssetInline)

    @admin.display(description="Game versions")
    def version_span(self, obj):
        start = obj.introduced_in or "Any"
        end = obj.removed_in or "current"
        return f"{start} – {end}"


@admin.register(CatalogueAlias)
class CatalogueAliasAdmin(admin.ModelAdmin):
    list_display = ("stable_id", "entry", "introduced_in", "removed_in")
    list_filter = ("entry__kind", "introduced_in", "removed_in")
    search_fields = ("stable_id", "entry__stable_id", "entry__display_name")


@admin.register(TraitDetails)
class TraitDetailsAdmin(admin.ModelAdmin):
    list_display = ("entry", "point_cost", "is_profession_trait", "disabled_in_multiplayer")
    list_filter = ("is_profession_trait", "disabled_in_multiplayer")
    search_fields = ("entry__display_name", "entry__stable_id", "description")
    autocomplete_fields = ("entry",)


@admin.register(OccupationDetails)
class OccupationDetailsAdmin(admin.ModelAdmin):
    list_display = ("entry", "point_cost")
    search_fields = ("entry__display_name", "entry__stable_id", "description")
    autocomplete_fields = ("entry",)


@admin.register(SkillDetails)
class SkillDetailsAdmin(admin.ModelAdmin):
    list_display = ("entry", "category", "is_passive")
    list_filter = ("is_passive", "category")
    search_fields = ("entry__display_name", "entry__stable_id", "description")
    autocomplete_fields = ("entry",)


@admin.register(ItemDetails)
class ItemDetailsAdmin(admin.ModelAdmin):
    list_display = (
        "entry",
        "pz_item_type",
        "display_category",
        "capability_summary",
        "weapon_skill",
    )
    list_filter = ("pz_item_type", "display_category", "weapon_skill")
    search_fields = (
        "entry__display_name",
        "entry__stable_id",
        "pz_item_type",
        "display_category__display_name",
        "display_category__stable_id",
        "weapon_skill__entry__display_name",
        "weapon_skill__entry__stable_id",
    )
    autocomplete_fields = ("entry", "display_category", "weapon_skill")
    readonly_fields = ("raw_properties",)

    @admin.display(description="Capabilities")
    def capability_summary(self, obj):
        return ", ".join(obj.capabilities)


@admin.register(ItemDisplayCategory)
class ItemDisplayCategoryAdmin(admin.ModelAdmin):
    list_display = ("display_name", "stable_id", "item_count")
    search_fields = ("display_name", "stable_id")

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(AnimalDetails)
class AnimalDetailsAdmin(admin.ModelAdmin):
    list_display = ("entry", "species_name", "species_id", "category", "life_stage")
    list_filter = ("category", "life_stage", "species_name")
    search_fields = (
        "entry__display_name",
        "entry__stable_id",
        "species_name",
        "species_id",
    )
    autocomplete_fields = ("entry",)


@admin.register(DeliverableDetails)
class DeliverableDetailsAdmin(admin.ModelAdmin):
    list_display = ("entry", "category")
    list_filter = ("category",)
    search_fields = ("entry__display_name", "entry__stable_id", "category")
    autocomplete_fields = ("entry",)


@admin.register(MapLocationVersion)
class MapLocationVersionAdmin(admin.ModelAdmin):
    list_display = (
        "entry", "location_type", "game_version", "registry_version", "anchor"
    )
    list_filter = ("location_type", "game_version", "registry_version")
    search_fields = ("entry__display_name", "entry__stable_id", "buildings__building_id")
    autocomplete_fields = ("entry",)
    inlines = (MapLocationBuildingInline,)

    @admin.display(description="Anchor")
    def anchor(self, obj):
        return f"{obj.anchor_x}, {obj.anchor_y}, {obj.anchor_z}"


@admin.register(MapLocationBuilding)
class MapLocationBuildingAdmin(admin.ModelAdmin):
    list_display = ("building_id", "location_version")
    list_filter = ("location_version__location_type", "location_version__game_version")
    search_fields = (
        "building_id", "location_version__entry__stable_id",
        "location_version__entry__display_name",
    )
    autocomplete_fields = ("location_version",)


@admin.register(CatalogueAsset)
class CatalogueAssetAdmin(admin.ModelAdmin):
    list_display = (
        "entry",
        "role",
        "source_key",
        "source_type",
        "availability",
        "game_availability",
        "imported_at",
    )
    list_filter = (
        "role",
        "source_type",
        "availability",
        "game_availability",
        "entry__kind",
    )
    search_fields = ("entry__display_name", "entry__stable_id", "source_key")
    autocomplete_fields = ("entry",)
    readonly_fields = (
        "game_availability",
        "game_source_path",
        "game_source_checksum",
    )

    def save_model(self, request, obj, form, change):
        if "file" in form.changed_data and obj.file:
            obj.source_type = CatalogueAsset.SourceType.MANUAL
            obj.availability = CatalogueAsset.Availability.IMPORTED
            obj.source_path = ""
            obj.source_checksum = ""
        super().save_model(request, obj, form, change)
