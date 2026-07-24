from django.contrib import admin

from .models import CatalogueAlias, CatalogueEntry


class CatalogueAliasInline(admin.TabularInline):
    model = CatalogueAlias
    extra = 0
    fields = ("stable_id", "introduced_in", "removed_in", "notes")


@admin.register(CatalogueEntry)
class CatalogueEntryAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "kind",
        "stable_id",
        "category",
        "version_span",
        "is_active",
        "updated_at",
    )
    list_filter = ("kind", "is_active", "introduced_in", "removed_in")
    search_fields = ("display_name", "stable_id", "category", "aliases__stable_id")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("kind", "stable_id", "display_name", "category")}),
        (
            "Game version applicability",
            {"fields": ("introduced_in", "removed_in", "is_active")},
        ),
        ("Presentation", {"fields": ("icon_key",)}),
        ("Catalogue record", {"fields": ("notes", "created_at", "updated_at")}),
    )
    inlines = (CatalogueAliasInline,)

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
