from django.contrib import admin

from .models import SiteBranding


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
