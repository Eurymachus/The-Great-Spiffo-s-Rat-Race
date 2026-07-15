from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

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
}


class Command(BaseCommand):
    help = "Create or update the standard Rat Race account roles."

    def handle(self, *args, **options):
        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            permissions = Permission.objects.filter(
                content_type__app_label="registry", codename__in=codenames
            )
            group.permissions.set(permissions)
        for participant in Participant.objects.prefetch_related("groups"):
            sync_staff_status(participant)
        self.stdout.write(self.style.SUCCESS("Rat Race roles are ready."))
