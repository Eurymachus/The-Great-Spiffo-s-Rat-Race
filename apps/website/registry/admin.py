import csv
import uuid

from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone

from .models import AccountClosureRecord, Participant
from .tokens import create_verification_token
from .verification_email import send_verification_email

admin.site.site_header = "The Rat Race administration"
admin.site.site_title = "The Rat Race admin"
admin.site.index_title = "Challenge administration"
admin.site.index_template = "admin/rat_race_index.html"
admin.site.app_index_template = "admin/rat_race_app_index.html"

REDACTED_PARTICIPANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def can_process_closures(user):
    return user.is_superuser or user.groups.filter(
        name="Challenge Administrator"
    ).exists()


def get_redacted_participant():
    redacted, created = Participant.objects.get_or_create(
        id=REDACTED_PARTICIPANT_ID,
        defaults={
            "nickname": "Redacted",
            "email": "redacted@rat-race.invalid",
            "status": Participant.Status.REMOVED,
            "is_active": False,
            "is_system_account": True,
            "privacy_notice_version": "system",
        },
    )
    if created:
        redacted.set_unusable_password()
        redacted.save(update_fields=("password",))
    return redacted


@admin.action(description="Export selected registrations as CSV")
def export_registrations(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="rat-race-participants.csv"'
    writer = csv.writer(response)
    writer.writerow(("nickname", "email", "status", "registered_at", "verified_at"))
    for participant in queryset.order_by("registered_at"):
        writer.writerow(
            (
                participant.nickname,
                participant.email,
                participant.status,
                participant.registered_at.isoformat(),
                participant.verified_at.isoformat() if participant.verified_at else "",
            )
        )
    return response


@admin.action(description="Resend verification to selected registrations")
def resend_verifications(modeladmin, request, queryset):
    eligible = queryset.filter(
        status__in=(Participant.Status.PENDING, Participant.Status.EXPIRED)
    )
    sent = 0
    for participant in eligible:
        verification_url = request.build_absolute_uri(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        send_verification_email(participant, verification_url)
        participant.status = Participant.Status.PENDING
        participant.verification_sent_at = timezone.now()
        participant.save(update_fields=("status", "verification_sent_at"))
        sent += 1
    modeladmin.message_user(
        request,
        f"Sent {sent} verification email(s).",
        level=messages.SUCCESS,
    )


def promote_to_role(modeladmin, request, queryset, role_name):
    role, _ = Group.objects.get_or_create(name=role_name)
    for participant in queryset:
        participant.groups.add(role)
    queryset.update(is_staff=True)
    modeladmin.message_user(request, f"Promoted {queryset.count()} participant(s) to {role_name}.", level=messages.SUCCESS)


@admin.action(description="Promote selected participants to Approver")
def promote_to_approver(modeladmin, request, queryset):
    promote_to_role(modeladmin, request, queryset, "Approver")


@admin.action(description="Promote selected participants to Moderator")
def promote_to_moderator(modeladmin, request, queryset):
    promote_to_role(modeladmin, request, queryset, "Moderator")


@admin.action(description="Promote selected participants to Challenge Administrator")
def promote_to_challenge_admin(modeladmin, request, queryset):
    promote_to_role(modeladmin, request, queryset, "Challenge Administrator")


@admin.action(description="Process closure and redact selected participants")
def process_account_closures(modeladmin, request, queryset):
    if not can_process_closures(request.user):
        modeladmin.message_user(
            request,
            "Only a Challenge Administrator can process account closures.",
            level=messages.ERROR,
        )
        return None

    eligible = queryset.filter(
        deletion_requested_at__isnull=False,
        is_system_account=False,
        is_staff=False,
    )
    skipped = queryset.count() - eligible.count()

    if request.POST.get("confirm") == "yes":
        redacted = get_redacted_participant()
        processed = 0
        for participant in eligible:
            with transaction.atomic():
                # Future run/report foreign keys must be reassigned to this
                # protected system participant here before deleting identity.
                # No participant-owned run records exist in the registry milestone.
                closure_reference = (
                    participant.deletion_request_reference or uuid.uuid4()
                )
                AccountClosureRecord.objects.get_or_create(
                    reference=closure_reference,
                    defaults={"requested_at": participant.deletion_requested_at},
                )
                participant.delete()
                processed += 1
        modeladmin.message_user(
            request,
            f"Processed {processed} account closure(s) beneath {redacted.nickname}. "
            f"Skipped {skipped} ineligible or staff account(s).",
            level=messages.SUCCESS,
        )
        return None

    context = {
        **modeladmin.admin_site.each_context(request),
        "title": "Confirm account closure and redaction",
        "queryset": eligible,
        "eligible_count": eligible.count(),
        "skipped_count": skipped,
        "action_checkbox_name": ACTION_CHECKBOX_NAME,
        "opts": modeladmin.model._meta,
    }
    return TemplateResponse(
        request, "admin/registry/confirm_account_closure.html", context
    )


@admin.register(Participant)
class ParticipantAdmin(UserAdmin):
    list_display = (
        "nickname",
        "email",
        "status",
        "registered_at",
        "verified_at",
        "deletion_requested_at",
    )
    list_filter = ("status", "registered_at", "deletion_requested_at")
    search_fields = ("nickname", "email")
    readonly_fields = (
        "id",
        "normalized_nickname",
        "normalized_email",
        "registered_at",
        "privacy_notice_acknowledged_at",
        "verification_sent_at",
        "deletion_requested_at",
        "is_system_account",
    )
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Participant", {"fields": ("nickname", "status", "verified_at", "admin_notes")}),
        ("Account closure request", {"fields": ("deletion_requested_at", "deletion_request_note")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Registration record", {"fields": ("id", "normalized_nickname", "normalized_email", "registered_at", "privacy_notice_acknowledged_at", "verification_sent_at", "privacy_notice_version", "is_system_account")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nickname", "password1", "password2", "is_active", "is_staff", "groups")}),
    )
    actions = (resend_verifications, promote_to_approver, promote_to_moderator, promote_to_challenge_admin, process_account_closures, export_registrations)
    date_hierarchy = "registered_at"

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_process_closures(request.user):
            actions.pop("process_account_closures", None)
        return actions


@admin.register(AccountClosureRecord)
class AccountClosureRecordAdmin(admin.ModelAdmin):
    list_display = ("reference", "requested_at", "processed_at")
    readonly_fields = ("reference", "requested_at", "processed_at")
    ordering = ("-processed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
