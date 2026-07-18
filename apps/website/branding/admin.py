from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .models import SiteBranding, WebsiteTheme
from .presets import THEME_PRESETS


def font_specimens(text):
    font_keys = (
        "system",
        "condensed",
        "slab",
        "oswald",
        "derelict",
        "derelict_rough",
        "humanist",
        "mono",
    )
    return format_html(
        '<span class="font-specimens" aria-label="Font example">{}</span>',
        format_html_join(
            "", '<span data-font="{}">{}</span>', ((key, text) for key in font_keys)
        ),
    )


class WebsiteThemeAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_font"].help_text = font_specimens(
            "The Great Spiffo's Rat Race"
        )
        self.fields["heading_font"].help_text = font_specimens(
            "Welcome to the Rat Race!"
        )
        self.fields["body_font"].help_text = font_specimens(
            "Your participant account is ready."
        )

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


@admin.action(description="Delete selected custom themes", permissions=("delete",))
def delete_custom_themes(modeladmin, request, queryset):
    branding = SiteBranding.current()
    active_theme_id = branding.active_theme_id if branding else None
    deletable = queryset.filter(preset_key="").exclude(pk=active_theme_id)
    deleted = deletable.count()
    skipped = queryset.count() - deleted
    deletable.delete()
    if deleted:
        modeladmin.message_user(
            request, f"Deleted {deleted} custom theme(s).", level=messages.SUCCESS
        )
    if skipped:
        modeladmin.message_user(
            request,
            f"Kept {skipped} active or built-in theme(s).",
            level=messages.WARNING,
        )


@admin.register(WebsiteTheme)
class WebsiteThemeAdmin(admin.ModelAdmin):
    form = WebsiteThemeAdminForm
    change_form_template = "admin/branding/websitetheme/change_form.html"
    list_display = (
        "name",
        "active_marker",
        "preview_link",
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
                    "display_font",
                    "display_font_weight",
                    "display_font_spacing",
                    "heading_font",
                    "heading_font_weight",
                    "heading_font_spacing",
                    "body_font",
                    "body_font_weight",
                    "body_font_spacing",
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
    actions = (
        activate_theme,
        duplicate_themes,
        restore_presets,
        delete_custom_themes,
    )

    class Media:
        css = {"all": ("branding/theme_admin.css",)}

    @admin.display(boolean=True, description="Active")
    def active_marker(self, obj):
        branding = SiteBranding.current()
        return bool(branding and branding.active_theme_id == obj.pk)

    @admin.display(description="Preview")
    def preview_link(self, obj):
        query = urlencode({"theme-preview": obj.pk})
        url = f"{reverse('registry:register')}?{query}"
        return format_html('<a class="button" href="{}">Preview</a>', url)

    def has_delete_permission(self, request, obj=None):
        permitted = super().has_delete_permission(request, obj)
        if not permitted or obj is None:
            return permitted
        branding = SiteBranding.current()
        return not obj.preset_key and (
            not branding or branding.active_theme_id != obj.pk
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


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
                    "active_theme",
                )
            },
        ),
        (
            "Participant terminology",
            {
                "fields": (
                    "participant_label",
                    "participant_plural_label",
                    "former_participant_label",
                    "run_update_label",
                    "run_update_plural_label",
                )
            },
        ),
        (
            "Images",
            {
                "description": (
                    "Each image is optional. Disabling an image keeps the upload "
                    "available for later and restores the normal text or colour fallback."
                ),
                "fields": (
                    "enable_header_logo",
                    "header_logo",
                    "header_logo_alt",
                    "header_logo_preview",
                    "enable_favicon",
                    "favicon",
                    "favicon_preview",
                    "enable_social_image",
                    "social_image",
                    "social_image_preview",
                    "enable_homepage_feature_image",
                    "homepage_feature_image",
                    "homepage_feature_image_alt",
                    "homepage_feature_image_preview",
                    "enable_background_image",
                    "background_image",
                    "background_image_preview",
                ),
            },
        ),
        (
            "Affiliation and attribution",
            {
                "fields": (
                    "disclaimer",
                    "show_attribution",
                    "attribution_text",
                    "attribution_url",
                    "attribution_new_tab",
                )
            },
        ),
        ("Record", {"fields": ("updated_at",)}),
    )
    readonly_fields = (
        "header_logo_preview",
        "favicon_preview",
        "social_image_preview",
        "homepage_feature_image_preview",
        "background_image_preview",
        "updated_at",
    )

    def _image_preview(self, obj, field_name, label):
        image = getattr(obj, field_name, None) if obj else None
        if not image:
            return format_html(
                '<span style="color:var(--body-quiet-color)">No {} uploaded - fallback remains active.</span>',
                label,
            )
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">'
            '<img src="{}" alt="" style="display:block;max-width:24rem;max-height:10rem;object-fit:contain;background:#202020;padding:.5rem;border-radius:4px">'
            '</a>',
            image.url,
            image.url,
        )

    @admin.display(description="Header logo preview")
    def header_logo_preview(self, obj):
        return self._image_preview(obj, "header_logo", "header logo")

    @admin.display(description="Favicon preview")
    def favicon_preview(self, obj):
        return self._image_preview(obj, "favicon", "favicon")

    @admin.display(description="Social sharing preview")
    def social_image_preview(self, obj):
        return self._image_preview(obj, "social_image", "social image")

    @admin.display(description="Homepage feature preview")
    def homepage_feature_image_preview(self, obj):
        return self._image_preview(obj, "homepage_feature_image", "homepage image")

    @admin.display(description="Background preview")
    def background_image_preview(self, obj):
        return self._image_preview(obj, "background_image", "background image")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["active_theme"].widget.can_delete_related = False
        return form

    def changelist_view(self, request, extra_context=None):
        branding = SiteBranding.current()
        if branding and self.has_view_or_change_permission(request, branding):
            return redirect(
                reverse("admin:branding_sitebranding_change", args=(branding.pk,))
            )
        if self.has_add_permission(request):
            return redirect(reverse("admin:branding_sitebranding_add"))
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return not SiteBranding.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
