import csv
import uuid
from pathlib import Path

from django.contrib import admin, messages
from django import forms
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from .models import (
    AccountClosureRecord,
    ChallengeRun,
    Notification,
    Participant,
    RunSubmission,
    StreamingAccount,
    StreamingMedia,
)
from .tokens import create_verification_token
from .verification_email import send_verification_email
from .avatar_moderation import approve_pending_avatar, reject_pending_avatar
from .notifications import notify
from .run_review import build_run_review
from .run_exports import decode_run_export

admin.site.site_header = f"{settings.SITE_SHORT_TITLE} administration"
admin.site.site_title = f"{settings.SITE_SHORT_TITLE} admin"
admin.site.index_title = "Challenge administration"
admin.site.index_template = "admin/rat_race_index.html"
admin.site.app_index_template = "admin/rat_race_app_index.html"


class ParticipantAdminForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Passwords are not stored in plaintext, so the existing password "
            "cannot be viewed. Use the password-change form to replace it."
        ),
    )
    avatar_status = forms.CharField(label="Avatar status", disabled=True, required=False)

    class Meta:
        model = Participant
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["avatar_status"] = self.instance.get_avatar_status_display()

    def clean_avatar_status(self):
        return self.instance.avatar_status

def can_process_closures(user):
    return user.is_superuser or user.groups.filter(
        name="Challenge Administrator"
    ).exists()

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


@admin.action(description="Approve selected pending avatars")
def approve_avatars(modeladmin, request, queryset):
    approved = sum(approve_pending_avatar(participant) for participant in queryset)
    modeladmin.message_user(request, f"Approved {approved} avatar(s).", level=messages.SUCCESS)


@admin.action(description="Reject selected pending avatars")
def reject_avatars(modeladmin, request, queryset):
    rejected = 0
    for participant in queryset.filter(avatar_status=Participant.AvatarStatus.PENDING):
        reject_pending_avatar(participant)
        rejected += 1
    modeladmin.message_user(request, f"Rejected {rejected} avatar(s).", level=messages.SUCCESS)


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


@admin.action(description="Promote selected participants to Branding Administrator")
def promote_to_branding_admin(modeladmin, request, queryset):
    promote_to_role(modeladmin, request, queryset, "Branding Administrator")


@admin.action(description="Promote selected participants to Zomboid Integration")
def promote_to_zomboid_integration(modeladmin, request, queryset):
    promote_to_role(modeladmin, request, queryset, "Zomboid Integration")


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
        is_staff=False,
    )
    skipped = queryset.count() - eligible.count()

    if request.POST.get("confirm") == "yes":
        processed = 0
        for participant in eligible:
            with transaction.atomic():
                # Future Run.participant foreign keys must use SET_NULL so the
                # participant identity is detached while each run survives.
                # The registry milestone does not have a Run model yet.
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
            f"Processed {processed} account closure(s). "
            f"Skipped {skipped} account(s) without a pending request or with staff access.",
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
    form = ParticipantAdminForm
    list_display = (
        "nickname",
        "email",
        "status",
        "avatar_status",
        "registered_at",
        "verified_at",
        "deletion_requested_at",
    )
    list_filter = ("status", "avatar_status", "registered_at", "deletion_requested_at")
    search_fields = ("nickname", "email")
    readonly_fields = (
        "id",
        "normalized_nickname",
        "normalized_email",
        "registered_at",
        "privacy_notice_acknowledged_at",
        "age_eligibility_confirmed_at",
        "verification_sent_at",
        "deletion_requested_at",
        "avatar_review_path",
        "avatar_moderation_note",
        "avatar_submitted_at",
        "avatar_review_preview",
    )
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Participant", {"fields": ("nickname", "status", "verified_at", "admin_notes")}),
        ("Avatar", {"fields": ("avatar", "avatar_status", "avatar_submitted_at", "avatar_review_preview", "avatar_review_path", "avatar_moderation_note")}),
        ("Account closure request", {"fields": ("deletion_requested_at", "deletion_request_note")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Registration record", {"fields": ("id", "normalized_nickname", "normalized_email", "registered_at", "privacy_notice_acknowledged_at", "privacy_notice_version", "age_eligibility_confirmed_at", "age_policy_version", "verification_sent_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nickname", "password1", "password2", "is_active", "is_staff", "groups")}),
    )
    actions = (approve_avatars, reject_avatars, resend_verifications, promote_to_approver, promote_to_moderator, promote_to_challenge_admin, promote_to_branding_admin, promote_to_zomboid_integration, process_account_closures, export_registrations)
    date_hierarchy = "registered_at"

    @admin.display(description="Pending avatar preview")
    def avatar_review_preview(self, obj):
        if not obj or not obj.avatar_review_path:
            return "No avatar is awaiting review."
        url = reverse("admin:registry_participant_avatar_review", args=(obj.pk,))
        approve_url = reverse("admin:registry_participant_avatar_approve", args=(obj.pk,))
        decline_url = reverse("admin:registry_participant_avatar_decline", args=(obj.pk,))
        return format_html(
            '<div style="display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;">'
            '<img src="{}" alt="Pending avatar" style="width:160px;height:160px;object-fit:cover;border-radius:50%;">'
            '<div class="avatar-review-actions">'
            '<button type="button" class="button avatar-review-approve" data-avatar-review-action="{}">Approve</button>'
            '<button type="button" class="button avatar-review-decline" data-avatar-review-action="{}">Decline</button>'
            '</div></div>',
            url, approve_url, decline_url,
        )

    def get_urls(self):
        return [
            path(
                "<path:object_id>/avatar-review/approve/",
                self.admin_site.admin_view(self.approve_avatar_view),
                name="registry_participant_avatar_approve",
            ),
            path(
                "<path:object_id>/avatar-review/decline/",
                self.admin_site.admin_view(self.decline_avatar_view),
                name="registry_participant_avatar_decline",
            ),
            path(
                "<path:object_id>/avatar-review/",
                self.admin_site.admin_view(self.avatar_review_image),
                name="registry_participant_avatar_review",
            ),
        ] + super().get_urls()

    def avatar_review_participant(self, request, object_id):
        participant = self.get_object(request, object_id)
        if not participant or not self.has_change_permission(request, participant):
            raise Http404
        return participant

    def approve_avatar_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        participant = self.avatar_review_participant(request, object_id)
        if approve_pending_avatar(participant):
            notify(participant, title="Avatar approved", message="Your new avatar has been approved and published.")
            self.message_user(request, "The avatar was approved and published.", level=messages.SUCCESS)
        else:
            self.message_user(request, "There was no pending avatar to approve.", level=messages.WARNING)
        return redirect("admin:registry_participant_change", participant.pk)

    def decline_avatar_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        participant = self.avatar_review_participant(request, object_id)
        if participant.avatar_status == Participant.AvatarStatus.PENDING:
            reject_pending_avatar(participant)
            notify(participant, title="Avatar declined", message="Your avatar was not accepted. Your previous avatar has not changed.")
            self.message_user(request, "The pending avatar was declined and removed.", level=messages.SUCCESS)
        else:
            self.message_user(request, "There was no pending avatar to decline.", level=messages.WARNING)
        return redirect("admin:registry_participant_change", participant.pk)

    def avatar_review_image(self, request, object_id):
        participant = self.get_object(request, object_id)
        if not participant or not self.has_view_or_change_permission(request, participant):
            raise Http404
        avatar_path = Path(settings.AVATAR_QUARANTINE_ROOT) / participant.avatar_review_path
        if not participant.avatar_review_path or not avatar_path.is_file():
            raise Http404
        return FileResponse(avatar_path.open("rb"), content_type="image/webp")

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_process_closures(request.user):
            actions.pop("process_account_closures", None)
        return actions

    class Media:
        css = {"all": ("registry/admin_avatar_review.css",)}
        js = ("registry/admin_avatar_review.js",)


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


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "category", "created_at", "read_at")
    list_filter = ("category", "created_at", "read_at")
    search_fields = ("title", "message", "recipient__nickname", "recipient__email")
    autocomplete_fields = ("recipient",)
    readonly_fields = ("created_at", "read_at")
    ordering = ("-created_at",)


@admin.register(StreamingAccount)
class StreamingAccountAdmin(admin.ModelAdmin):
    list_display = (
        "participant", "provider", "display_name", "status", "connected_at",
    )
    list_filter = ("provider", "status", "connected_at")
    search_fields = (
        "participant__nickname", "participant__email", "display_name",
        "provider_identity", "channel_identity",
    )
    autocomplete_fields = ("participant",)
    readonly_fields = (
        "provider_identity", "channel_identity", "connected_at", "refreshed_at",
        "token_expires_at", "token_validated_at",
        "provider_metadata",
    )

    def get_exclude(self, request, obj=None):
        return ("encrypted_access_token", "encrypted_refresh_token")

    def has_add_permission(self, request):
        return False


@admin.register(StreamingMedia)
class StreamingMediaAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "account",
        "provider_media_id",
        "published_at",
        "refreshed_at",
    )
    list_filter = ("kind", "account__provider", "published_at", "refreshed_at")
    search_fields = (
        "title",
        "provider_media_id",
        "account__display_name",
        "account__participant__email",
    )
    autocomplete_fields = ("account",)
    readonly_fields = (
        "provider_media_id",
        "parent_media_id",
        "title",
        "canonical_url",
        "thumbnail_url",
        "published_at",
        "duration_seconds",
        "vod_offset_seconds",
        "metadata_snapshot",
        "refreshed_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(ChallengeRun)
class ChallengeRunAdmin(admin.ModelAdmin):
    list_display = (
        "run_id", "participant", "character_name", "lifecycle_status", "status",
        "current_kills", "event_sequence", "updated_at",
    )
    list_filter = (
        "lifecycle_status", "status", "export_format", "bootstrapped", "updated_at"
    )
    search_fields = ("run_id", "character_name", "participant__nickname", "participant__email")
    readonly_fields = (
        "participant", "status", "approved_submission",
        "run_id", "export_format", "generated_at", "current_kills",
        "event_sequence", "event_hash", "character_name", "bootstrapped",
        "latest_projection", "latest_events", "first_submitted_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RunSubmission)
class RunSubmissionAdmin(admin.ModelAdmin):
    change_form_template = "admin/registry/runsubmission/change_form.html"
    list_display = (
        "run", "submitter", "status", "current_kills",
        "event_sequence", "submitted_at",
    )
    list_filter = ("status", "export_format", "submitted_at")
    search_fields = ("run__run_id", "run__character_name", "submitter__nickname")
    autocomplete_fields = ("run", "submitter")
    readonly_fields = (
        "run", "baseline_submission", "submitter", "checksum", "raw_export", "export_format",
        "generated_at", "current_kills", "event_sequence", "event_hash",
        "submitted_at", "evidence_provider", "evidence_media_type",
        "evidence_media_id", "evidence_url", "evidence_title",
        "evidence_start_seconds", "evidence_end_seconds", "evidence_clips",
        "projection", "reviewed_at", "review_note",
    )

    class Media:
        css = {"all": ("registry/admin_run_review.css",)}

    def change_view(self, request, object_id, form_url="", extra_context=None):
        submission = self.get_object(request, object_id)
        context = dict(extra_context or {})
        if submission:
            context["run_review"] = build_run_review(submission)
        return super().change_view(request, object_id, form_url, context)

    def get_urls(self):
        return [
            path(
                "<path:object_id>/approve/",
                self.admin_site.admin_view(self.approve_submission_view),
                name="registry_runsubmission_approve",
            ),
            path(
                "<path:object_id>/decline/",
                self.admin_site.admin_view(self.decline_submission_view),
                name="registry_runsubmission_decline",
            ),
        ] + super().get_urls()

    def review_submission(self, request, object_id):
        submission = self.get_object(request, object_id)
        if not submission or not self.has_change_permission(request, submission):
            raise Http404
        return submission

    def approve_submission_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        submission = self.review_submission(request, object_id)
        if submission.status != RunSubmission.Status.RECEIVED:
            self.message_user(request, "This submission has already been reviewed.", level=messages.WARNING)
            return redirect("admin:registry_runsubmission_change", submission.pk)
        baseline = submission.run.approved_submission
        if baseline and submission.event_sequence <= baseline.event_sequence:
            self.message_user(
                request,
                "This submission does not advance beyond the current approved snapshot.",
                level=messages.ERROR,
            )
            return redirect("admin:registry_runsubmission_change", submission.pk)
        decoded = decode_run_export(submission.raw_export)
        reviewed_at = timezone.now()
        submission.status = RunSubmission.Status.APPROVED
        submission.reviewed_at = reviewed_at
        submission.review_note = ""
        submission.save(update_fields=("status", "reviewed_at", "review_note"))
        run = submission.run
        run.status = ChallengeRun.Status.OFFICIAL
        run.approved_submission = submission
        run.export_format = decoded.format
        run.generated_at = decoded.generated_at
        run.current_kills = decoded.current_kills
        run.event_sequence = decoded.event_sequence
        run.event_hash = decoded.event_hash
        run.character_name = decoded.character_name
        run.bootstrapped = decoded.bootstrapped
        run.latest_projection = decoded.projection
        run.latest_events = decoded.events
        run.save()
        if run.participant:
            notify(
                run.participant,
                category=Notification.Category.SUBMISSION,
                title="Submission approved",
                message="Your Rat Race submission has been approved.",
                destination=reverse("registry:account"),
            )
        self.message_user(request, "The submission was approved.", level=messages.SUCCESS)
        return redirect("admin:registry_runsubmission_change", submission.pk)

    def decline_submission_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        submission = self.review_submission(request, object_id)
        if submission.status != RunSubmission.Status.RECEIVED:
            self.message_user(request, "This submission has already been reviewed.", level=messages.WARNING)
            return redirect("admin:registry_runsubmission_change", submission.pk)
        reason = request.POST.get("reason", "").strip()
        if not reason:
            self.message_user(
                request, "A reason is required when declining a submission.", level=messages.ERROR
            )
            return redirect("admin:registry_runsubmission_change", submission.pk)
        submission.status = RunSubmission.Status.DECLINED
        submission.reviewed_at = timezone.now()
        submission.review_note = reason
        submission.save(update_fields=("status", "reviewed_at", "review_note"))
        if submission.run.participant:
            notify(
                submission.run.participant,
                category=Notification.Category.SUBMISSION,
                title="Submission declined",
                message=f"Your Rat Race submission was not approved: {reason}",
                destination=reverse("registry:account"),
            )
        self.message_user(request, "The submission was declined.", level=messages.SUCCESS)
        return redirect("admin:registry_runsubmission_change", submission.pk)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
