from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import WebsiteSettings


@admin.register(WebsiteSettings)
class WebsiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Image upload restrictions",
            {"fields": ("maximum_image_upload_size",)},
        ),
        ("Record", {"fields": ("updated_at",)}),
    )
    readonly_fields = ("updated_at",)

    def changelist_view(self, request, extra_context=None):
        settings = WebsiteSettings.current()
        if settings and self.has_change_permission(request, settings):
            return redirect(
                reverse(
                    "admin:administration_websitesettings_change",
                    args=(settings.pk,),
                )
            )
        return super().changelist_view(request, extra_context=extra_context)

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
