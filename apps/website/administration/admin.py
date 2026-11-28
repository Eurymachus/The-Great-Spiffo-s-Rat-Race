from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import WebsiteSettings
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from .forms import ProviderConfigurationForm
from .models import ProviderConfiguration, ReleaseConfiguration
from config.release_controls import environment_state
from .provider_credentials import ProviderConfigurationError, get_provider_credentials



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


@admin.register(ProviderConfiguration)
class ProviderConfigurationAdmin(admin.ModelAdmin):
    form = ProviderConfigurationForm
    list_display = ('provider', 'source', 'site_origin', 'configuration_status', 'updated_at')
    fields = ('provider', 'source', 'client_id', 'tenant_id', 'redirect_uri', 'replacement_secret',
              'site_origin', 'configuration_status', 'updated_at')
    readonly_fields = ('site_origin', 'configuration_status', 'updated_at')
    actions = None

    def get_fields(self, request, obj=None):
        fields = list(self.fields)
        provider = obj.provider if obj else request.POST.get('provider', request.GET.get('provider', ''))
        if provider:
            if provider != 'graph':
                fields.remove('tenant_id')
            if provider in {'openai', 'steam'}:
                fields.remove('client_id')
            if provider not in {'discord', 'twitch', 'youtube'}:
                fields.remove('redirect_uri')
        return fields

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('provider',) if obj else ())

    @admin.display(description='Configuration status')
    def configuration_status(self, obj):
        if not obj or not obj.pk:
            return 'Not saved'
        try:
            credentials = get_provider_credentials(obj.provider)
            return 'Credentials available' if credentials.client_secret else 'Not configured or disabled'
        except ProviderConfigurationError:
            return 'Configuration unavailable; check site binding and encryption key'

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    @method_decorator(sensitive_post_parameters('replacement_secret'))
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        return super().changeform_view(request, object_id, form_url, extra_context)

    def construct_change_message(self, request, form, formsets, add=False):
        # Only field names are audited. Never include posted values or ciphertext.
        fields = [name for name in form.changed_data if name in
                  {'provider', 'source', 'client_id', 'tenant_id', 'redirect_uri', 'replacement_secret'}]
        return [{'changed': {'fields': fields}}] if fields else []


@admin.register(ReleaseConfiguration)
class ReleaseConfigurationAdmin(admin.ModelAdmin):
    fields = ("construction", "registration", "workshop_submissions", "rr1_submissions", "rr2", "updated_at")
    readonly_fields = ("updated_at",)
    actions = None

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request) and not ReleaseConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_changeform_initial_data(self, request):
        return environment_state()

    def changelist_view(self, request, extra_context=None):
        if self.has_module_permission(request):
            name = "change" if ReleaseConfiguration.objects.filter(pk=1).exists() else "add"
            return redirect(reverse("admin:administration_releaseconfiguration_" + name,
                                    args=(1,) if name == "change" else None))
        return super().changelist_view(request, extra_context)
