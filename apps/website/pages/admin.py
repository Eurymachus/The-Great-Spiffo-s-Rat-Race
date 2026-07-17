from django.contrib import admin

from .models import Page, PageSection, SectionItem


class PageSectionInline(admin.StackedInline):
    model = PageSection
    extra = 0
    show_change_link = True
    fields = (
        "position",
        "section_type",
        "is_visible",
        "small_heading",
        "main_heading",
        "introduction",
        "visitor_primary_button",
        "visitor_secondary_link",
        "signed_in_button",
    )


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Page", {"fields": ("title", "slug", "is_published")}),
        ("Record", {"fields": ("updated_at",)}),
    )
    inlines = (PageSectionInline,)

    def has_add_permission(self, request):
        return not Page.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        permitted = super().has_delete_permission(request, obj)
        return permitted and (obj is None or obj.slug != "home")

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if obj and obj.slug == "home":
            fields.append("slug")
        return fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


class SectionItemInline(admin.StackedInline):
    model = SectionItem
    extra = 0
    fields = ("position", "heading", "description")


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    list_display = ("page", "section_type", "position", "is_visible")
    list_filter = ("page", "section_type", "is_visible")
    list_select_related = ("page",)
    inlines = (SectionItemInline,)
    fieldsets = (
        (
            "Section",
            {"fields": ("page", "position", "section_type", "is_visible")},
        ),
        (
            "Introduction and actions",
            {
                "description": (
                    "These fields are used by an Introduction and actions section."
                ),
                "fields": (
                    "small_heading",
                    "main_heading",
                    "introduction",
                    "visitor_primary_button",
                    "visitor_secondary_link",
                    "signed_in_button",
                ),
            },
        ),
    )

    def get_model_perms(self, request):
        return {}


@admin.register(SectionItem)
class SectionItemAdmin(admin.ModelAdmin):
    list_display = ("heading", "section", "position")
    list_filter = ("section__page",)
    list_select_related = ("section", "section__page")

    def get_model_perms(self, request):
        return {}
