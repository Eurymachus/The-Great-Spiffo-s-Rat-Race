from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse

from .models import SiteBranding, WebsiteTheme
from .presets import THEME_PRESETS


class WebsiteThemeAdminForm(forms.ModelForm):
    class Meta:
        model = WebsiteTheme
        fields = "__all__"
        widgets = {
            field: forms.TextInput(attrs={"type": "color"})
            for field in (
                "background_colour",
                "background_highlight_colour",
                "surface_colour",
                "surface_alt_colour",
                "text_colour",
                "muted_text_colour",
                "accent_colour",
                "accent_hover_colour",
                "accent_text_colour",
                "border_colour",
                "success_colour",
                "error_colour",
            )
        }


@admin.action(description="Activate selected theme")
def activate_theme(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request, "Select exactly one theme to activate.", level=messages.ERROR
        )
        return None
    branding, _ = SiteBranding.objects.get_or_create(pk=SiteBranding.SINGLETON_PK)
    branding.active_theme = queryset.first()
    branding.save()
    modeladmin.message_user(
        request, f"Activated {branding.active_theme.name}.", level=messages.SUCCESS
    )


@admin.action(description="Preview selected theme on signup page")
def preview_theme(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request, "Select exactly one theme to preview.", level=messages.ERROR
        )
        return None
    query = urlencode({"theme-preview": queryset.first().pk})
    return redirect(f"{reverse('registry:register')}?{query}")


@admin.action(description="Duplicate selected themes")
def duplicate_themes(modeladmin, request, queryset):
    created = 0
    editable_fields = [
        field.name
        for field in WebsiteTheme._meta.fields
        if field.name not in {"id", "name", "preset_key", "updated_at"}
    ]
    for theme in queryset:
        base_name = f"Copy of {theme.name}"
        name = base_name
        suffix = 2
        while WebsiteTheme.objects.filter(name=name).exists():
            name = f"{base_name} {suffix}"
            suffix += 1
        WebsiteTheme.objects.create(
            name=name,
            **{field: getattr(theme, field) for field in editable_fields},
        )
        created += 1
    modeladmin.message_user(
        request, f"Created {created} theme copy/copies.", level=messages.SUCCESS
    )


@admin.action(description="Restore selected built-in presets")
def restore_presets(modeladmin, request, queryset):
    restored = 0
    for theme in queryset.exclude(preset_key=""):
        values = THEME_PRESETS.get(theme.preset_key)
        if values:
            for field, value in values.items():
                if field != "name":
                    setattr(theme, field, value)
            theme.save()
            restored += 1
    modeladmin.message_user(
        request, f"Restored {restored} built-in preset(s).", level=messages.SUCCESS
    )


@admin.register(WebsiteTheme)
class WebsiteThemeAdmin(admin.ModelAdmin):
    form = WebsiteThemeAdminForm
    list_display = (
        "name",
        "active_marker",
        "colour_scheme",
        "background_style",
        "heading_font",
        "updated_at",
    )
    list_filter = ("colour_scheme", "background_style", "heading_font")
    search_fields = ("name",)
    readonly_fields = ("preset_key", "updated_at")
    fieldsets = (
        ("Theme", {"fields": ("name", "preset_key", "colour_scheme")}),
        (
            "Typography and shape",
            {
                "fields": (
                    "heading_font",
                    "body_font",
                    "corner_style",
                    "shadow_style",
                    "background_style",
                )
            },
        ),
        (
            "Colours",
            {
                "fields": (
                    "background_colour",
                    "background_highlight_colour",
                    "surface_colour",
                    "surface_alt_colour",
                    "text_colour",
                    "muted_text_colour",
                    "accent_colour",
                    "accent_hover_colour",
                    "accent_text_colour",
                    "border_colour",
                    "success_colour",
                    "error_colour",
                )
            },
        ),
        ("Record", {"fields": ("updated_at",)}),
    )
    actions = (activate_theme, preview_theme, duplicate_themes, restore_presets)

    @admin.display(boolean=True, description="Active")
    def active_marker(self, obj):
        branding = SiteBranding.current()
        return bool(branding and branding.active_theme_id == obj.pk)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteBranding)
class SiteBrandingAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Challenge identity",
            {
                "fields": (
                    "full_title",
                    "short_title",
                    "tagline",
                    "welcome_message",
                    "former_participant_label",
                    "active_theme",
                )
            },
        ),
        ("Affiliation", {"fields": ("disclaimer",)}),
        ("Record", {"fields": ("updated_at",)}),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not SiteBranding.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
