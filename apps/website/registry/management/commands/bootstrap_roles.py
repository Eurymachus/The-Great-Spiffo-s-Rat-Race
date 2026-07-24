from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from branding.models import SiteBranding, WebsiteTheme
from branding.presets import THEME_PRESETS
from registry.models import Participant
from registry.signals import sync_staff_status


ROLE_PERMISSIONS = {
    "Participant": (),
    "Approver": ("view_participant",),
    "Moderator": ("view_participant", "change_participant"),
    "Challenge Administrator": (
        "add_participant",
        "view_participant",
        "change_participant",
        "view_accountclosurerecord",
    ),
    "Branding Administrator": (
        "view_sitebranding",
        "change_sitebranding",
        "add_websitetheme",
        "view_websitetheme",
        "change_websitetheme",
        "delete_websitetheme",
        "add_managedimage",
        "view_managedimage",
        "change_managedimage",
        "delete_managedimage",
        "view_page",
        "change_page",
        "delete_page",
        "add_pagesection",
        "view_pagesection",
        "change_pagesection",
        "delete_pagesection",
        "add_sectionitem",
        "view_sectionitem",
        "change_sectionitem",
        "delete_sectionitem",
    ),
}

ZOMBOID_INTEGRATION_PERMISSIONS = (
    "add_catalogueentry",
    "view_catalogueentry",
    "change_catalogueentry",
    "delete_catalogueentry",
    "add_cataloguealias",
    "view_cataloguealias",
    "change_cataloguealias",
    "delete_cataloguealias",
)


class Command(BaseCommand):
    help = "Create or update the standard Rat Race account roles."

    def handle(self, *args, **options):
        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            permissions = Permission.objects.filter(
                content_type__app_label__in=("registry", "branding", "pages"),
                codename__in=codenames,
            )
            group.permissions.set(permissions)
        integration_group, _ = Group.objects.get_or_create(name="Zomboid Integration")
        integration_group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="zomboid_catalogue",
                codename__in=ZOMBOID_INTEGRATION_PERMISSIONS,
            )
        )
        themes = {}
        for preset_key, values in THEME_PRESETS.items():
            themes[preset_key], _ = WebsiteTheme.objects.get_or_create(
                preset_key=preset_key, defaults=values
            )
        branding, _ = SiteBranding.objects.get_or_create(pk=SiteBranding.SINGLETON_PK)
        if not branding.active_theme_id:
            branding.active_theme = themes["survival-event"]
            branding.save()
        for participant in Participant.objects.prefetch_related("groups"):
            sync_staff_status(participant)
        self.stdout.write(self.style.SUCCESS("Rat Race roles are ready."))
