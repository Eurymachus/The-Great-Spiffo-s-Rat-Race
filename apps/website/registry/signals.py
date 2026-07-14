from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Participant


STAFF_ROLE_NAMES = {"Approver", "Moderator", "Challenge Administrator"}


def sync_staff_status(participant):
    if participant.is_superuser:
        return
    should_be_staff = participant.groups.filter(name__in=STAFF_ROLE_NAMES).exists()
    if participant.is_staff != should_be_staff:
        Participant.objects.filter(pk=participant.pk).update(is_staff=should_be_staff)
        participant.is_staff = should_be_staff


@receiver(m2m_changed, sender=Participant.groups.through)
def participant_groups_changed(sender, instance, action, reverse, **kwargs):
    if not reverse and action in {"post_add", "post_remove", "post_clear"}:
        sync_staff_status(instance)
