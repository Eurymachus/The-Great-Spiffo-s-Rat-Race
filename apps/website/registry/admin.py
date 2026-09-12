import csv
import uuid
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote

from django.contrib import admin, messages
from django import forms
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.db import transaction, OperationalError
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotAllowed, QueryDict
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from .models import (
    AccountClosureRecord,
    ChallengeMode,
    ChallengeModeAlias,
    ChallengeRun,
    LegacyDataImport,
    LegacyRun,
    LegacyRunClaim,
    LegacyRunSubmission,
    ExploitRuling,
    ExploitRulingImage,
    Notification,
    Participant,
    ParticipantChallengeModeLimit,
    RunSubmission,
    SubmissionAudit,
    SubmissionAuditEntry,
    StreamingAccount,
    StreamingMedia,
    WorkshopMod,
    WorkshopModVote,
)
from .legacy_imports import apply_legacy_import, create_legacy_import_review
from .legacy_submissions import legacy_submission_strength
from .run_authority import refresh_initial_run_authority
from .run_block_cache import attach_verified_blocks, decode_run_export_cached


def locked_run_submission_queryset():
    return RunSubmission.objects.select_for_update(of=("self",)).select_related(
        "run", "run__approved_submission"
    )


class ExploitRulingImageInline(admin.TabularInline):
    model = ExploitRulingImage
    extra = 0
    fields = ("image", "alternative_text", "caption", "position")
    ordering = ("position", "pk")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "image" and formfield:
            widget = formfield.widget
            select_widget = getattr(widget, "widget", widget)
            select_widget.attrs["class"] = (
                f"{select_widget.attrs.get('class', '')} media-library-select".strip()
            )
            select_widget.attrs["data-library-url"] = reverse(
                "admin:branding_managedimage_library"
            )
            for permission_name in (
                "can_add_related",
                "can_change_related",
                "can_delete_related",
                "can_view_related",
            ):
                if hasattr(widget, permission_name):
                    setattr(widget, permission_name, False)
        return formfield


@admin.register(ExploitRuling)
class ExploitRulingAdmin(admin.ModelAdmin):
    list_display = ("title", "classification", "is_published", "position", "updated_at")
    list_editable = ("classification", "is_published", "position")
    list_filter = ("classification", "is_published")
    search_fields = ("title", "ruling", "guidance")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Ruling", {"fields": ("title", "slug", "classification", "ruling", "guidance")}),
        ("Publishing", {"fields": ("is_published", "position")}),
    )
    inlines = (ExploitRulingImageInline,)

    class Media:
        css = {"all": ("branding/media_library.css",)}
        js = ("branding/media_library.js",)


@admin.register(LegacyRun)
class LegacyRunAdmin(admin.ModelAdmin):
    list_display = (
        "legacy_participant_name", "lifecycle", "claimed_participant",
        "current_submission", "best_submission", "updated_at",
    )
    list_filter = ("lifecycle",)
    search_fields = ("legacy_participant_name", "claimed_participant__nickname")
    readonly_fields = (
        "source_key", "normalized_legacy_name", "current_submission", "best_submission",
        "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(LegacyRunSubmission)
class LegacyRunSubmissionAdmin(admin.ModelAdmin):
    change_form_template = "admin/registry/legacyrunsubmission/change_form.html"
    list_display = (
        "run", "source", "status", "source_rank", "zombie_kills",
        "outposts_cleared", "maxed_skills", "submitted_at",
    )
    list_filter = ("source", "status")
    search_fields = ("run__legacy_participant_name", "run__claimed_participant__nickname")
    readonly_fields = (
        "run", "source", "status", "source_rank", "character_name", "zombie_kills",
        "survival_time_input", "survival_time_full", "survival_days", "outposts_cleared",
        "maxed_skills", "challenge_progress", "reports_death", "import_review",
        "submitted_by", "submitted_at", "evidence_provider", "evidence_media_type",
        "evidence_media_id", "evidence_url", "evidence_title", "evidence_start_seconds",
        "evidence_end_seconds", "reviewed_by", "reviewed_at", "review_note",
    )

    class Media:
        css = {"all": ("registry/admin_run_review.css", "registry/admin_legacy_claim_review.css")}

    def changelist_view(self, request, extra_context=None):
        context = dict(extra_context or {})
        context["title"] = "Legacy run submission reviews"
        return super().changelist_view(request, extra_context=context)

    def get_urls(self):
        return [
            path("<path:object_id>/approve/", self.admin_site.admin_view(self.approve_submission_view), name="registry_legacyrunsubmission_approve"),
            path("<path:object_id>/decline/", self.admin_site.admin_view(self.decline_submission_view), name="registry_legacyrunsubmission_decline"),
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
        with transaction.atomic():
            submission = LegacyRunSubmission.objects.select_for_update().select_related("run", "submitted_by").get(pk=submission.pk)
            run = LegacyRun.objects.select_for_update().select_related("best_submission").get(pk=submission.run_id)
            if submission.source != LegacyRunSubmission.Source.PARTICIPANT or submission.status != LegacyRunSubmission.Status.RECEIVED:
                self.message_user(request, "This legacy submission is not awaiting review.", level=messages.WARNING)
                return redirect("admin:registry_legacyrunsubmission_change", submission.pk)
            if run.claimed_participant_id != submission.submitted_by_id:
                self.message_user(request, "The submission no longer belongs to the participant linked to this run.", level=messages.ERROR)
                return redirect("admin:registry_legacyrunsubmission_change", submission.pk)

            submission.status = LegacyRunSubmission.Status.APPROVED
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.review_note = request.POST.get("review_note", "").strip()
            submission.save(update_fields=("status", "reviewed_by", "reviewed_at", "review_note"))
            run.current_submission = submission
            run.character_name = submission.character_name
            if run.best_submission_id is None or legacy_submission_strength(submission) > legacy_submission_strength(run.best_submission):
                run.best_submission = submission
            if submission.reports_death:
                run.lifecycle = LegacyRun.Lifecycle.DECEASED
            run.save(update_fields=("current_submission", "best_submission", "character_name", "lifecycle", "updated_at"))

        notify(
            submission.submitted_by,
            category=Notification.Category.SUBMISSION,
            title="Legacy update approved",
            message="Your legacy Rat Race update has been approved.",
            destination=reverse("registry:account"),
        )
        self.message_user(request, "The legacy run update was approved.", level=messages.SUCCESS)
        return redirect("admin:registry_legacyrunsubmission_change", submission.pk)

    def decline_submission_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        submission = self.review_submission(request, object_id)
        reason = request.POST.get("reason", "").strip()
        if not reason:
            self.message_user(request, "A reason is required when declining a legacy update.", level=messages.ERROR)
            return redirect("admin:registry_legacyrunsubmission_change", submission.pk)
        with transaction.atomic():
            submission = LegacyRunSubmission.objects.select_for_update().select_related("submitted_by").get(pk=submission.pk)
            if submission.source != LegacyRunSubmission.Source.PARTICIPANT or submission.status != LegacyRunSubmission.Status.RECEIVED:
                self.message_user(request, "This legacy submission is not awaiting review.", level=messages.WARNING)
                return redirect("admin:registry_legacyrunsubmission_change", submission.pk)
            submission.status = LegacyRunSubmission.Status.DECLINED
            submission.reviewed_by = request.user
            submission.reviewed_at = timezone.now()
            submission.review_note = reason
            submission.save(update_fields=("status", "reviewed_by", "reviewed_at", "review_note"))
        notify(
            submission.submitted_by,
            category=Notification.Category.SUBMISSION,
            title="Legacy update declined",
            message=f"Your legacy Rat Race update was not approved: {reason}",
            destination=reverse("registry:account"),
        )
        self.message_user(request, "The legacy run update was declined.", level=messages.SUCCESS)
        return redirect("admin:registry_legacyrunsubmission_change", submission.pk)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LegacyRunClaim)
class LegacyRunClaimAdmin(admin.ModelAdmin):
    change_form_template = "admin/registry/legacyrunclaim/change_form.html"
    list_display = ("run", "participant", "status", "submitted_at", "reviewed_by", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("run__legacy_participant_name", "participant__nickname")
    readonly_fields = (
        "run", "participant", "status", "evidence", "submitted_at",
        "reviewed_by", "reviewed_at", "review_note",
    )
    fields = readonly_fields

    class Media:
        css = {"all": (
            "registry/admin_run_review.css",
            "registry/admin_legacy_claim_review.css",
        )}

    def changelist_view(self, request, extra_context=None):
        context = dict(extra_context or {})
        context["title"] = "Legacy run claim reviews"
        return super().changelist_view(request, extra_context=context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        context = dict(extra_context or {})
        context["title"] = "Review legacy run claim"
        return super().change_view(request, object_id, form_url, context)

    def get_urls(self):
        return [
            path(
                "<path:object_id>/approve/",
                self.admin_site.admin_view(self.approve_claim_view),
                name="registry_legacyrunclaim_approve",
            ),
            path(
                "<path:object_id>/decline/",
                self.admin_site.admin_view(self.decline_claim_view),
                name="registry_legacyrunclaim_decline",
            ),
        ] + super().get_urls()

    def review_claim(self, request, object_id):
        claim = self.get_object(request, object_id)
        if not claim or not self.has_change_permission(request, claim):
            raise Http404
        return claim

    def approve_claim_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        claim = self.review_claim(request, object_id)
        with transaction.atomic():
            claim = LegacyRunClaim.objects.select_for_update().select_related(
                "run", "participant"
            ).get(pk=claim.pk)
            run = LegacyRun.objects.select_for_update().get(pk=claim.run_id)
            if claim.status != LegacyRunClaim.Status.PENDING:
                self.message_user(request, "This claim has already been reviewed.", level=messages.WARNING)
                return redirect("admin:registry_legacyrunclaim_change", claim.pk)
            if run.claimed_participant_id and run.claimed_participant_id != claim.participant_id:
                self.message_user(request, "This legacy run is already linked to another participant.", level=messages.ERROR)
                return redirect("admin:registry_legacyrunclaim_change", claim.pk)
            if LegacyRun.objects.select_for_update().filter(
                claimed_participant=claim.participant
            ).exclude(pk=run.pk).exists():
                self.message_user(request, "This participant is already linked to another legacy run.", level=messages.ERROR)
                return redirect("admin:registry_legacyrunclaim_change", claim.pk)

            reviewed_at = timezone.now()
            run.claimed_participant = claim.participant
            run.save(update_fields=("claimed_participant", "updated_at"))
            claim.status = LegacyRunClaim.Status.APPROVED
            claim.reviewed_by = request.user
            claim.reviewed_at = reviewed_at
            claim.review_note = request.POST.get("review_note", "").strip()
            claim.save(update_fields=("status", "reviewed_by", "reviewed_at", "review_note"))

        self.message_user(request, "The legacy run claim was approved.", level=messages.SUCCESS)
        notify(
            claim.participant,
            category=Notification.Category.ACCOUNT,
            title="Legacy run claim approved",
            message=f"Your historical Rat Race record for {run.legacy_participant_name} is now linked to your account.",
            destination=reverse("registry:account"),
        )
        return redirect("admin:registry_legacyrunclaim_change", claim.pk)

    def decline_claim_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        claim = self.review_claim(request, object_id)
        reason = request.POST.get("reason", "").strip()
        if not reason:
            self.message_user(request, "A reason is required when declining a claim.", level=messages.ERROR)
            return redirect("admin:registry_legacyrunclaim_change", claim.pk)
        with transaction.atomic():
            claim = LegacyRunClaim.objects.select_for_update().get(pk=claim.pk)
            if claim.status != LegacyRunClaim.Status.PENDING:
                self.message_user(request, "This claim has already been reviewed.", level=messages.WARNING)
                return redirect("admin:registry_legacyrunclaim_change", claim.pk)
            claim.status = LegacyRunClaim.Status.DECLINED
            claim.reviewed_by = request.user
            claim.reviewed_at = timezone.now()
            claim.review_note = reason
            claim.save(update_fields=("status", "reviewed_by", "reviewed_at", "review_note"))

        self.message_user(request, "The legacy run claim was declined.", level=messages.SUCCESS)
        notify(
            claim.participant,
            category=Notification.Category.ACCOUNT,
            title="Legacy run claim declined",
            message=f"Your claim for {claim.run.legacy_participant_name} was not approved: {reason}",
            destination=reverse("registry:account"),
        )
        return redirect("admin:registry_legacyrunclaim_change", claim.pk)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LegacyDataImportUploadForm(forms.Form):
    legacy_leaderboard = forms.FileField(
        help_text="Upload the final Legacy Leaderboard CSV exported from Google Sheets."
    )
    legacy_hall_of_fame = forms.FileField(
        help_text="Upload the final Legacy Hall of Fame CSV exported from Google Sheets."
    )


@admin.register(LegacyDataImport)
class LegacyDataImportAdmin(admin.ModelAdmin):
    change_list_template = "admin/registry/legacydataimport/change_list.html"
    change_form_template = "admin/registry/legacydataimport/change_form.html"
    list_display = (
        "uploaded_at", "status", "leaderboard_filename", "hall_of_fame_filename",
        "uploaded_by", "imported_at",
    )
    list_filter = ("status",)
    readonly_fields = (
        "id", "status", "leaderboard_filename", "hall_of_fame_filename",
        "leaderboard_sha256", "hall_of_fame_sha256",
        "uploaded_by", "uploaded_at", "imported_at",
    )
    exclude = ("leaderboard_csv", "hall_of_fame_csv", "preview")

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        return [
            path("upload/", self.admin_site.admin_view(self.upload_view), name="registry_legacydataimport_upload"),
            path(
                "<uuid:object_id>/confirm/", self.admin_site.admin_view(self.confirm_view),
                name="registry_legacydataimport_confirm",
            ),
        ] + super().get_urls()

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = dict(extra_context or {})
        review = self.get_object(request, object_id) if object_id else None
        if review and review.preview:
            records = review.preview.get("records", [])

            def position(record, source):
                value = (record.get(source) or {}).get("rank")
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 10**9

            extra_context["legacy_leaderboard_preview"] = sorted(
                (record for record in records if record.get("leaderboard")),
                key=lambda record: (position(record, "leaderboard"), record.get("legacy_participant_name", "").casefold()),
            )
            extra_context["legacy_hall_of_fame_preview"] = sorted(
                (record for record in records if record.get("hall_of_fame")),
                key=lambda record: (position(record, "hall_of_fame"), record.get("legacy_participant_name", "").casefold()),
            )
        return super().changeform_view(request, object_id, form_url, extra_context)

    def upload_view(self, request):
        if not request.user.is_superuser:
            raise Http404
        form = LegacyDataImportUploadForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                review = create_legacy_import_review(
                    leaderboard_upload=form.cleaned_data["legacy_leaderboard"],
                    hall_of_fame_upload=form.cleaned_data["legacy_hall_of_fame"],
                    uploaded_by=request.user,
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, "Legacy files validated. Review the preview before importing.")
                return redirect("admin:registry_legacydataimport_change", review.pk)
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Upload legacy data",
            "form": form,
        }
        return TemplateResponse(request, "admin/registry/legacydataimport/upload.html", context)

    def confirm_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        review = self.get_object(request, object_id)
        if review is None:
            raise Http404
        try:
            apply_legacy_import(review, request.user)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, "Legacy Leaderboard and Hall of Fame data imported successfully.")
        return redirect("admin:registry_legacydataimport_change", object_id)
from .tokens import create_verification_token
from .verification_email import send_verification_email
from .avatar_moderation import approve_pending_avatar, reject_pending_avatar
from .notifications import notify
from .run_review import build_challenge_run_overview, build_run_review
from .run_exports import decode_run_export
from .challenge_modes import resolve_challenge_mode


PUBLIC_MOD_RATIONALE_TEMPLATES = {
    "Allowed": (
        "This mod is purely cosmetic and does not alter gameplay or game balance.",
        "This mod improves presentation or usability without revealing information unavailable in the unmodified game.",
        "This mod clarifies information already available in the unmodified game without adding new gameplay data.",
    ),
    "Disallowed": (
        "This mod alters gameplay or game balance beyond the permitted cosmetic and quality-of-life scope.",
        "This mod provides gameplay information that is not available in the unmodified game.",
        "This mod automates gameplay, progression or another action that must be performed by the participant.",
        "This mod adds or improves player abilities, protection, insulation, traits, occupations, items or vehicles.",
    ),
}


class WorkshopModAdminForm(forms.ModelForm):
    class Meta:
        model = WorkshopMod
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        ruling = cleaned_data.get("ruling")
        previous_ruling = self.instance.ruling if self.instance.pk else None
        if (
            previous_ruling == WorkshopMod.Ruling.PENDING
            and ruling in {WorkshopMod.Ruling.ALLOWED, WorkshopMod.Ruling.DISALLOWED}
            and not (cleaned_data.get("public_rationale") or "").strip()
        ):
            self.add_error(
                "public_rationale",
                "Enter the public reason for this final ruling.",
            )
        return cleaned_data


@admin.register(WorkshopMod)
class WorkshopModAdmin(admin.ModelAdmin):
    form = WorkshopModAdminForm
    change_form_template = "admin/registry/workshopmod/change_form.html"
    change_list_template = "admin/registry/workshopmod/change_list.html"
    actions = (
        "allow_selected_mods",
        "disallow_selected_mods",
        "reset_selected_rulings",
    )
    list_display = (
        "title",
        "workshop_id",
        "ruling",
        "is_recommended",
        "previous_unstable_ruling",
        "submitted_by",
        "review_action",
        "updated_at",
    )
    list_filter = ("ruling", "is_recommended", "previous_unstable_ruling")
    search_fields = ("title", "workshop_id", "submission_reason")
    readonly_fields = (
        "workshop_id",
        "title",
        "steam_url",
        "preview_url",
        "creator_steam_id",
        "submitted_by",
        "submission_reason",
        "steam_checked_at",
        "reviewed_by",
        "reviewed_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Decision", {"fields": ("ruling", "public_rationale", "is_recommended")}),
        ("Participant request", {"fields": ("submitted_by", "submission_reason", "created_at")}),
        ("Previous Unstable policy", {"fields": ("previous_unstable_ruling", "unstable_ruling_notes")}),
        ("Review audit", {"fields": ("reviewed_by", "reviewed_at", "updated_at")}),
        ("Steam Workshop metadata", {"classes": ("collapse",), "fields": ("workshop_id", "title", "steam_url", "preview_url", "creator_steam_id", "steam_checked_at")}),
    )

    class Media:
        css = {"all": ("registry/admin_mod_review.css",)}
        js = ("registry/admin_mod_review.js",)

    def get_urls(self):
        return [
            path(
                "<path:object_id>/vote/",
                self.admin_site.admin_view(self.vote_view),
                name="registry_workshopmod_vote",
            ),
        ] + super().get_urls()

    @staticmethod
    def can_vote(user):
        return user.is_superuser or user.groups.filter(
            name__in=("Workshop Mod Approver", "Challenge Administrator")
        ).exists()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        context = dict(extra_context or {})
        if obj:
            votes = list(obj.team_votes.select_related("voter"))
            counts = {
                choice: sum(vote.decision == choice for vote in votes)
                for choice in WorkshopModVote.Decision.values
            }
            if counts[WorkshopModVote.Decision.DISCUSS] or (
                counts[WorkshopModVote.Decision.ALLOW]
                and counts[WorkshopModVote.Decision.DISALLOW]
            ):
                recommendation = "Discussion needed"
            elif counts[WorkshopModVote.Decision.ALLOW]:
                recommendation = "Recommend Allow"
            elif counts[WorkshopModVote.Decision.DISALLOW]:
                recommendation = "Recommend Disallow"
            else:
                recommendation = "Awaiting team votes"
            context.update(
                {
                    "mod_votes": votes,
                    "mod_vote_counts": counts,
                    "mod_vote_recommendation": recommendation,
                    "can_vote_on_mod": self.can_vote(request.user)
                    and obj.ruling == WorkshopMod.Ruling.PENDING,
                    "current_mod_vote": next(
                        (vote for vote in votes if vote.voter_id == request.user.pk),
                        None,
                    ),
                    "public_rationale_templates": PUBLIC_MOD_RATIONALE_TEMPLATES,
                }
            )
        return super().change_view(request, object_id, form_url, context)

    def vote_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404
        change_url = reverse("admin:registry_workshopmod_change", args=(obj.pk,))
        if not self.can_vote(request.user):
            self.message_user(request, "You are not eligible to vote on mod rulings.", messages.ERROR)
            return redirect(change_url)
        if obj.ruling != WorkshopMod.Ruling.PENDING:
            self.message_user(request, "Voting is closed because this mod has a final ruling.", messages.ERROR)
            return redirect(change_url)

        decision = request.POST.get("decision", "")
        reason = request.POST.get("reason", "").strip()
        if decision not in WorkshopModVote.Decision.values:
            self.message_user(request, "Choose Allow, Disallow or Discuss.", messages.ERROR)
            return redirect(change_url)
        if decision in {
            WorkshopModVote.Decision.DISALLOW,
            WorkshopModVote.Decision.DISCUSS,
        } and not reason:
            self.message_user(request, "Enter a reason for a Disallow or Discuss vote.", messages.ERROR)
            return redirect(change_url)

        WorkshopModVote.objects.update_or_create(
            workshop_mod=obj,
            voter=request.user,
            defaults={
                "voter_name": request.user.nickname or request.user.email,
                "decision": decision,
                "reason": reason,
            },
        )
        self.message_user(request, "Your team vote has been recorded.", messages.SUCCESS)
        return redirect(change_url)

    @admin.display(description="Review")
    def review_action(self, obj):
        label = "Review" if obj.ruling == WorkshopMod.Ruling.PENDING else "View"
        return format_html(
            '<a class="button" href="{}">{}</a>',
            reverse("admin:registry_workshopmod_change", args=(obj.pk,)),
            label,
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if "o" not in request.GET:
            queryset = queryset.order_by(
                Case(
                    When(ruling=WorkshopMod.Ruling.PENDING, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                "title",
                "workshop_id",
            )
        return queryset

    def changelist_view(self, request, extra_context=None):
        context = dict(extra_context or {})
        context["pending_mod_review_count"] = WorkshopMod.objects.filter(
            ruling=WorkshopMod.Ruling.PENDING
        ).count()
        context["title"] = "Mod approval queue"
        return super().changelist_view(request, extra_context=context)

    def save_model(self, request, obj, form, change):
        previous_ruling = None
        if obj.pk:
            previous_ruling = WorkshopMod.objects.filter(pk=obj.pk).values_list(
                "ruling", flat=True
            ).first()
        if obj.ruling == WorkshopMod.Ruling.PENDING:
            obj.reviewed_by = None
            obj.reviewed_at = None
        elif (
            obj.ruling in {WorkshopMod.Ruling.ALLOWED, WorkshopMod.Ruling.DISALLOWED}
            and obj.ruling != previous_ruling
        ):
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("allow_selected_mods", None)
            actions.pop("disallow_selected_mods", None)
            actions.pop("reset_selected_rulings", None)
        return actions

    @admin.action(description="Allow selected mods")
    def allow_selected_mods(self, request, queryset):
        reviewed_at = timezone.now()
        updated = queryset.exclude(
            ruling=WorkshopMod.Ruling.REQUIRED
        ).update(
            ruling=WorkshopMod.Ruling.ALLOWED,
            reviewed_by=request.user,
            reviewed_at=reviewed_at,
            updated_at=reviewed_at,
        )
        self.message_user(request, f"{updated} mod(s) marked Allowed.", messages.SUCCESS)

    @admin.action(description="Disallow selected mods")
    def disallow_selected_mods(self, request, queryset):
        reviewed_at = timezone.now()
        updated = queryset.exclude(
            ruling=WorkshopMod.Ruling.REQUIRED
        ).update(
            ruling=WorkshopMod.Ruling.DISALLOWED,
            is_recommended=False,
            reviewed_by=request.user,
            reviewed_at=reviewed_at,
            updated_at=reviewed_at,
        )
        self.message_user(
            request,
            f"{updated} mod(s) marked Disallowed.",
            messages.SUCCESS,
        )

    @admin.action(description="Reset ruling")
    def reset_selected_rulings(self, request, queryset):
        updated = queryset.exclude(
            ruling=WorkshopMod.Ruling.REQUIRED
        ).update(
            ruling=WorkshopMod.Ruling.PENDING,
            is_recommended=False,
            public_rationale="",
            reviewed_by=None,
            reviewed_at=None,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} mod ruling(s) reset to Pending review.",
            messages.SUCCESS,
        )

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


@admin.action(description="Promote selected participants to Workshop Mod Approver")
def promote_to_workshop_mod_approver(modeladmin, request, queryset):
    promote_to_role(modeladmin, request, queryset, "Workshop Mod Approver")


@admin.action(description="Promote selected participants to Run Submission Approver")
def promote_to_run_submission_approver(modeladmin, request, queryset):
    promote_to_role(modeladmin, request, queryset, "Run Submission Approver")


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
    actions = (approve_avatars, reject_avatars, resend_verifications, promote_to_workshop_mod_approver, promote_to_run_submission_approver, promote_to_moderator, promote_to_challenge_admin, promote_to_branding_admin, promote_to_zomboid_integration, process_account_closures, export_registrations)
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


class ChallengeModeAliasInline(admin.TabularInline):
    model = ChallengeModeAlias
    extra = 0


@admin.register(ChallengeMode)
class ChallengeModeAdmin(admin.ModelAdmin):
    list_display = (
        "display_name", "key", "game_mode_name", "evidence_required", "max_active_runs_per_participant",
        "max_pending_deceased_runs_per_participant",
        "is_active", "display_order",
    )
    list_editable = ("evidence_required", "max_active_runs_per_participant", "max_pending_deceased_runs_per_participant", "is_active", "display_order")
    search_fields = ("display_name", "key", "game_mode_name", "aliases__key")
    inlines = (ChallengeModeAliasInline,)


@admin.register(ParticipantChallengeModeLimit)
class ParticipantChallengeModeLimitAdmin(admin.ModelAdmin):
    list_display = ("participant", "challenge_mode", "max_active_runs", "max_pending_deceased_runs", "expires_at", "set_by")
    list_filter = ("challenge_mode", "expires_at")
    search_fields = ("participant__nickname", "participant__email", "reason")
    autocomplete_fields = ("participant", "challenge_mode")
    readonly_fields = ("set_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        obj.set_by = request.user
        super().save_model(request, obj, form, change)


class RunModerationHistoryMixin:
    object_history_template = "admin/registry/run_history.html"

    def history_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        context = dict(extra_context or {})
        events = []
        if obj and self.has_view_or_change_permission(request, obj):
            submissions = obj.submissions.all() if isinstance(obj, ChallengeRun) else RunSubmission.objects.filter(pk=obj.pk)
            for sub in submissions.select_related("submitter", "reviewed_by", "evidence_requested_by").prefetch_related("audit_entries__reviewer"):
                label = str(sub.pk)
                events.append({"date": sub.submitted_at, "actor": sub.submitter or "Former participant", "action": "Submission received", "detail": "", "submission": label})
                if sub.reviewed_at:
                    events.append({"date": sub.reviewed_at, "actor": "Automatic approval" if sub.approval_method == "automatic" else sub.reviewed_by or "Former reviewer", "action": sub.get_status_display(), "detail": sub.review_note, "submission": label})
                if sub.evidence_requested_at:
                    events.append({"date": sub.evidence_requested_at, "actor": sub.evidence_requested_by or "System", "action": "Evidence requested", "detail": sub.evidence_request_note, "submission": label})
                for audit in sub.audit_entries.all():
                    events.append({"date": audit.created_at, "actor": audit.reviewer or "Former reviewer", "action": "Audit: " + audit.get_outcome_display(), "detail": audit.note, "submission": label})
            run = obj if isinstance(obj, ChallengeRun) else obj.run
            if run.participant_deactivated_at:
                events.append({"date": run.participant_deactivated_at, "actor": run.participant or "Former participant", "action": "Run deactivated", "detail": "Participant deactivation recorded.", "submission": ""})
            events.sort(key=lambda event: event["date"], reverse=True)
        context["moderation_events"] = events
        return super().history_view(request, object_id, context)


@admin.register(ChallengeRun)
class ChallengeRunAdmin(RunModerationHistoryMixin, admin.ModelAdmin):
    change_form_template = "admin/registry/challengerun/change_form.html"
    change_list_template = "admin/registry/challengerun/change_list.html"
    list_display = (
        "run_id", "participant", "character_name", "challenge_mode", "lifecycle_status", "status",
        "current_kills", "event_sequence", "updated_at",
    )
    list_filter = (
        "challenge_mode", "lifecycle_status", "status", "export_format", "bootstrapped", "updated_at"
    )
    search_fields = ("run_id", "character_name", "participant__nickname", "participant__email")
    readonly_fields = (
        "participant", "status", "approved_submission", "challenge_mode", "lifecycle_status",
        "challenge_id", "challenge_game_mode",
        "starting_challenge_mode", "starting_challenge_id",
        "starting_challenge_game_mode",
        "run_id", "export_format", "generated_at", "current_kills",
        "event_sequence", "event_hash", "character_name", "bootstrapped",
        "latest_projection", "latest_events", "participant_deactivated_at",
        "first_submitted_at", "updated_at",
    )

    class Media:
        css = {"all": ("registry/admin_run_review.css",)}

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "participant", "challenge_mode", "approved_submission"
        )

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            raise Http404

        from .run_saved_views import resolve_view, apply_work_filters, manage_view
        if request.method == "POST":
            return manage_view(request)
        params, view_context = resolve_view(request)

        runs = self.get_queryset(request).annotate(submission_count=Count("submissions"))
        search = params.get("q", "").strip()
        if search:
            runs = runs.filter(
                Q(run_id__icontains=search)
                | Q(character_name__icontains=search)
                | Q(participant__nickname__icontains=search)
                | Q(participant__email__icontains=search)
            )

        def filter_values(runs, params):
            challenge_mode = params.get("challenge_mode", "")
            if challenge_mode == "unmapped":
                runs = runs.filter(challenge_mode__isnull=True)
            elif challenge_mode:
                runs = runs.filter(challenge_mode_id=challenge_mode)

            lifecycle_status = params.get("lifecycle_status", "")
            if lifecycle_status in ChallengeRun.Lifecycle.values:
                runs = runs.filter(lifecycle_status=lifecycle_status)

            verification_status = params.get("status", "")
            if verification_status in ChallengeRun.Status.values:
                runs = runs.filter(status=verification_status)

            export_format = params.get("export_format", "")
            if export_format.isdigit():
                runs = runs.filter(export_format=int(export_format))

            bootstrapped = params.get("bootstrapped", "")
            if bootstrapped in {"yes", "no"}:
                runs = runs.filter(bootstrapped=bootstrapped == "yes")

            updated = params.get("updated", "")
            now = timezone.now()
            if updated == "today":
                runs = runs.filter(updated_at__date=timezone.localdate())
            elif updated == "7days":
                runs = runs.filter(updated_at__gte=now - timedelta(days=7))
            elif updated == "month":
                runs = runs.filter(updated_at__gte=now - timedelta(days=30))
            elif updated == "year":
                runs = runs.filter(updated_at__gte=now - timedelta(days=365))

            runs = apply_work_filters(runs, params)
            return runs
        for filter_key in ("challenge_mode", "lifecycle_status", "status", "export_format", "bootstrapped", "updated", "work", "audit", "vod"):
            values = [value for value in params.get(filter_key, "").split(",") if value]
            if values:
                matching = Q(pk__in=[])
                for value in values:
                    matching |= Q(pk__in=filter_values(runs, {filter_key: value}).values("pk"))
                runs = runs.filter(matching)
        runs = apply_work_filters(runs, {})
        challenge_mode = params.get("challenge_mode", "")
        lifecycle_status = params.get("lifecycle_status", "")
        verification_status = params.get("status", "")
        export_format = params.get("export_format", "")
        bootstrapped = params.get("bootstrapped", "")
        updated = params.get("updated", "")
        table_headers = []
        current_sort = params.get("sort") or "-updated_at"
        for label, field in [("Run", "character_name"), ("Participant", "participant__nickname"), ("Lifecycle", "lifecycle_status"), ("Verification", "status"), ("Kills", "current_kills"), ("Events", "event_sequence"), ("Submissions / Work", "submission_count"), ("Updated", "updated_at")]:
            header_params = params.copy()
            header_params.pop("page", None)
            header_params["sort"] = "-" + field if current_sort == field else field
            table_headers.append({"label": label, "url": "?" + header_params.urlencode(), "direction": ("descending" if current_sort.startswith("-") else "ascending") if current_sort.lstrip("-") == field else "none"})
        view_context["table_headers"] = table_headers
        filtered_count = runs.count()
        paginator = Paginator(runs.order_by(params.get("sort") or "-updated_at", "pk"), 50)
        try:
            page_number = max(1, int(params.get("page", "1")))
        except ValueError:
            page_number = 1
        page = paginator.get_page(page_number)
        from django.db.models import Prefetch
        page.object_list = page.object_list.prefetch_related(Prefetch(
            "submissions", queryset=RunSubmission.objects.filter(status__in=("received", "awaiting_evidence")).order_by("submitted_at", "pk"), to_attr="pending_reviews"))
        for run in page.object_list:
            oldest = run.pending_reviews[0] if run.pending_reviews else None
            run.direct_review_url = (reverse("admin:registry_runsubmission_change", args=(oldest.pk,)) + "?return_to_run=1&run_tab=submissions") if oldest and params.get("work") == "review" else ""
            if params.get("audit") and not run.direct_review_url and run.approved_submission_id:
                run.direct_review_url = reverse("admin:registry_runsubmission_change", args=(run.approved_submission_id,)) + "?return_to_run=1&run_tab=audits"
            from .run_review import current_review_reasons
            run.review_findings = current_review_reasons(oldest) if oldest else []




        query = params.copy()
        query.pop("page", None)
        additional_filter_count = sum(
            bool(value)
            for value in (
                verification_status,
                export_format,
                bootstrapped,
                updated,
            )
        )
        context = {
            **self.admin_site.each_context(request),
            **view_context,
            "title": "Challenge Runs",
            "opts": self.model._meta,
            "runs": page.object_list,
            "page": page,
            "filtered_count": filtered_count,
            "search": search,
            "selected_challenge_mode": challenge_mode,
            "selected_lifecycle_status": lifecycle_status,
            "selected_status": verification_status,
            "selected_export_format": export_format,
            "selected_bootstrapped": bootstrapped,
            "selected_updated": updated,
            "additional_filter_count": additional_filter_count,
            "challenge_modes": ChallengeMode.objects.filter(is_active=True).order_by("display_name"),
            "lifecycle_choices": ChallengeRun.Lifecycle.choices,
            "status_choices": ChallengeRun.Status.choices,
            "export_formats": ChallengeRun.objects.order_by("export_format").values_list("export_format", flat=True).distinct(),
            "query_without_page": query.urlencode(),
        }
        return TemplateResponse(
            request,
            "admin/registry/challengerun/change_list.html",
            context,
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        return [
            path(
                "<path:object_id>/set-status/",
                self.admin_site.admin_view(self.set_status_view),
                name="registry_challengerun_set_status",
            ),
        ] + super().get_urls()

    @transaction.atomic
    def set_status_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        run = self.get_object(request, object_id)
        if not run or not self.has_change_permission(request, run):
            raise Http404

        status = request.POST.get("lifecycle_status", "").strip()
        reason = request.POST.get("reason", "").strip()
        valid_statuses = {value for value, _label in ChallengeRun.Lifecycle.choices}
        change_url = reverse("admin:registry_challengerun_change", args=(run.pk,))
        if status not in valid_statuses:
            return redirect(f"{change_url}?status_error=invalid_status")
        if not reason:
            return redirect(f"{change_url}?status_error=reason_required")

        previous_status = run.get_lifecycle_status_display()
        run.lifecycle_status = status
        run.save(update_fields=("lifecycle_status", "updated_at"))
        new_status = run.get_lifecycle_status_display()
        self.log_change(
            request,
            run,
            f'Lifecycle status changed from "{previous_status}" to "{new_status}". Reason: {reason}',
        )
        self.message_user(
            request,
            f"Lifecycle status set to {new_status}.",
            level=messages.SUCCESS,
        )
        return redirect(change_url)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        context = dict(extra_context or {})
        run = self.get_object(request, object_id)
        if run:
            context["run_overview"] = build_challenge_run_overview(run)
            context["run_tab"] = request.GET.get("tab", "overview")
            if context["run_tab"] not in {"overview", "submissions", "audits"}:
                context["run_tab"] = "overview"
            context["run_audit_submissions"] = run.submissions.filter(status="approved").prefetch_related("audit_entries__reviewer").order_by("submitted_at", "pk")
            context["next_review_id"] = run.submissions.filter(status__in=RunSubmission.moderation_queue_statuses()).order_by("submitted_at", "pk").values_list("pk", flat=True).first()
            context["pending_statuses"] = RunSubmission.moderation_queue_statuses() if run.lifecycle_status not in {"invalidated"} else ()
            context["run_submissions"] = run.submissions.select_related(
                "submitter", "reviewed_by", "challenge_mode"
            ).order_by(
                "generated_at", "submitted_at", "pk"
            )
            if context["run_tab"] == "submissions":
                from .run_review import current_review_summary
                for submission in context["run_submissions"]:
                    submission.run = run
                    submission.current_review = current_review_summary(submission)
        context["lifecycle_choices"] = ChallengeRun.Lifecycle.choices
        context["status_error"] = request.GET.get("status_error", "")
        return super().change_view(request, object_id, form_url, context)


class RunSubmissionApprovalFilter(admin.SimpleListFilter):
    title = "approval"
    parameter_name = "approval_state"

    def lookups(self, request, model_admin):
        return (
            ("approved", "Approved"),
            ("unapproved", "Unapproved"),
            ("declined", "Declined"),
        )

    def queryset(self, request, queryset):
        if self.value() == "approved":
            return queryset.filter(status=RunSubmission.Status.APPROVED)
        if self.value() == "unapproved":
            return queryset.filter(
                status__in=RunSubmission.moderation_queue_statuses()
            )
        if self.value() == "declined":
            return queryset.filter(status=RunSubmission.Status.DECLINED)
        return queryset


@admin.register(RunSubmission)
class RunSubmissionAdmin(RunModerationHistoryMixin, admin.ModelAdmin):
    change_form_template = "admin/registry/runsubmission/change_form.html"
    list_display = (
        "run", "submitter", "review_status", "first_approval", "current_kills",
        "event_sequence", "submitted_at",
    )
    list_filter = (RunSubmissionApprovalFilter, "export_format", "submitted_at")
    actions = None
    search_fields = ("run__run_id", "run__character_name", "submitter__nickname")
    autocomplete_fields = ("run", "submitter")
    readonly_fields = (
        "run", "baseline_submission", "submitter", "checksum", "raw_export", "export_format",
        "generated_at", "current_kills", "event_sequence", "event_hash",
        "challenge_mode", "challenge_id", "challenge_game_mode",
        "submitted_at", "evidence_provider", "evidence_media_type",
        "evidence_media_id", "evidence_url", "evidence_title",
        "evidence_start_seconds", "evidence_end_seconds", "evidence_clips",
        "projection", "reviewed_at", "review_note",
        "reviewed_by", "evidence_requested_at", "evidence_requested_by",
        "evidence_request_note",
        "preapproval_state", "preapproval_findings", "preapproval_version",
        "preapproval_assessed_at", "approval_method", "approval_policy_version",
        "routing_reasons", "evidence_check", "evidence_checked_at",
    )

    class Media:
        css = {"all": ("registry/admin_run_review.css",)}

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "run", "run__approved_submission", "baseline_submission", "submitter",
            "challenge_mode",
        ).prefetch_related("evidence_revisions")

    @admin.display(description="Approval")
    def first_approval(self, submission):
        if submission.baseline_submission_id is None:
            return format_html(
                '<span class="run-review-list-badge is-first">First approval</span>'
            )
        return ""

    @admin.display(description="Status", ordering="status")
    def review_status(self, submission):
        if submission.status == RunSubmission.Status.APPROVED and submission.approval_method == "automatic":
            return format_html('<span class="run-review-list-badge">{}</span>', "Auto-Approved")
        if submission.status == RunSubmission.Status.APPROVED:
            return format_html(
                '<span class="run-review-list-badge status-approved"><span aria-hidden="true">✓</span> Approved</span>'
            )
        if submission.status == RunSubmission.Status.DECLINED:
            return format_html(
                '<span class="run-review-list-badge status-declined"><span aria-hidden="true">!</span> Declined</span>'
            )
        if submission.status == RunSubmission.Status.AWAITING_EVIDENCE:
            return format_html(
                '<span class="run-review-list-badge finding-warning"><span aria-hidden="true">△</span> Awaiting evidence</span>'
            )
        severity, icon, label = {
            RunSubmission.PreapprovalState.GREEN: ("pass", "✓", "All checks passed"),
            RunSubmission.PreapprovalState.ORANGE: ("warning", "△", "Needs attention"),
            RunSubmission.PreapprovalState.RED: ("danger", "!", "Blocking issue"),
        }[submission.preapproval_state]
        if any(
            finding.get("title") == "Invalid export"
            for finding in submission.preapproval_findings
            if isinstance(finding, dict)
        ):
            label = "Invalid export"
        return format_html(
            '<span class="run-review-list-badge finding-{}"><span aria-hidden="true">{}</span> {}</span>',
            severity, icon, label,
        )

    def changelist_view(self, request, extra_context=None):
        if request.method == "GET":
            from .models import RunSavedView
            view = RunSavedView.objects.filter(system_key="review").first()
            return redirect(reverse("admin:registry_challengerun_changelist") + (f"?view={view.pk}&reset=1" if view else ""))
        if not self.has_view_permission(request):
            raise Http404
        params = request.GET
        if not request.META.get("QUERY_STRING"):
            saved_filters = unquote(
                request.COOKIES.get("rat_race_admin_run_submission_filters", "")
            )
            if saved_filters:
                params = QueryDict(saved_filters)
        pending = RunSubmission.objects.filter(
            status__in=RunSubmission.moderation_queue_statuses()
        ).select_related("run", "run__participant", "run__challenge_mode")
        search = params.get("q", "").strip()
        if search:
            pending = pending.filter(
                Q(run__character_name__icontains=search)
                | Q(run__run_id__icontains=search)
                | Q(submitter__nickname__icontains=search)
            )
        challenge_mode = params.get("challenge_mode", "")
        if challenge_mode:
            pending = pending.filter(challenge_mode_id=challenge_mode)
        queue_state = params.get("queue_state", "")
        pending_rows = list(pending.order_by("run_id", "submitted_at", "pk"))
        grouped = {}
        severity_rank = {
            RunSubmission.PreapprovalState.GREEN: 0,
            RunSubmission.PreapprovalState.ORANGE: 1,
            RunSubmission.PreapprovalState.RED: 2,
        }
        for submission in pending_rows:
            group = grouped.setdefault(
                submission.run_id,
                {
                    "run": submission.run,
                    "submissions": [],
                    "worst_state": RunSubmission.PreapprovalState.GREEN,
                },
            )
            group["submissions"].append(submission)
            if severity_rank[submission.preapproval_state] > severity_rank[group["worst_state"]]:
                group["worst_state"] = submission.preapproval_state
                group["worst_label"] = next(
                    (
                        finding.get("title")
                        for finding in submission.preapproval_findings
                        if finding.get("title")
                        and finding.get("level")
                        == (
                            "danger"
                            if submission.preapproval_state == RunSubmission.PreapprovalState.RED
                            else "warning"
                        )
                    ),
                    "Blocking issue" if submission.preapproval_state == RunSubmission.PreapprovalState.RED else "Needs attention",
                )
        runs = []
        for group in grouped.values():
            group["pending_count"] = len(group["submissions"])
            group["oldest_pending"] = group["submissions"][0]
            group["newest_pending"] = group["submissions"][-1]
            group["first_approval_pending"] = group["run"].approved_submission_id is None
            if queue_state == "first" and not group["first_approval_pending"]:
                continue
            if queue_state == "attention" and group["worst_state"] == RunSubmission.PreapprovalState.GREEN:
                continue
            if queue_state == "clean" and group["worst_state"] != RunSubmission.PreapprovalState.GREEN:
                continue
            runs.append(group)
        runs.sort(key=lambda group: group["oldest_pending"].submitted_at)
        context = {
            **self.admin_site.each_context(request),
            "title": "Submission Reviews",
            "opts": self.model._meta,
            "runs": runs,
            "search": search,
            "queue_state": queue_state,
            "selected_challenge_mode": challenge_mode,
            "challenge_modes": ChallengeMode.objects.filter(is_active=True).order_by(
                "display_name"
            ),
        }
        return TemplateResponse(
            request,
            "admin/registry/runsubmission/change_list.html",
            context,
        )

    def run_queue_view(self, request, run_id):
        if not self.has_view_permission(request):
            raise Http404
        if request.method == "POST" and not self.has_change_permission(request):
            raise Http404
        run = ChallengeRun.objects.select_related(
            "participant", "challenge_mode", "approved_submission"
        ).filter(pk=run_id).first()
        if run is None:
            raise Http404
        pending = list(
            run.submissions.filter(status__in=RunSubmission.moderation_queue_statuses())
            .select_related("submitter", "challenge_mode")
            .order_by("submitted_at", "pk")
        )
        if request.method == "POST":
            return HttpResponseNotAllowed(("GET",))
        for index, submission in enumerate(pending):
            submission.is_next_pending = index == 0
            submission.status_badge = self.review_status(submission)
        history = run.submissions.exclude(
            status__in=RunSubmission.moderation_queue_statuses()
        ).order_by("-submitted_at")
        context = {
            **self.admin_site.each_context(request),
            "title": f"Moderate {run}",
            "opts": self.model._meta,
            "run": run,
            "pending_submissions": pending,
            "history": history,
        }
        return TemplateResponse(
            request,
            "admin/registry/runsubmission/run_queue.html",
            context,
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        submission = self.get_object(request, object_id)
        if request.method == "POST":
            return HttpResponseNotAllowed(("GET",))
        context = dict(extra_context or {})
        if submission:
            if not self.has_view_or_change_permission(request, submission):
                raise PermissionDenied
            context["review_unavailable"] = submission.run.lifecycle_status in {"invalidated"}
            if not context["review_unavailable"] and submission.status in RunSubmission.moderation_queue_statuses():
                first = submission.run.submissions.filter(status__in=RunSubmission.moderation_queue_statuses()).order_by("submitted_at", "pk").first()
                if first and first.pk != submission.pk:
                    self.message_user(request, "Review the earlier submission first. Later submissions will be reassessed after that decision.", level=messages.INFO)
                    return redirect(reverse("admin:registry_challengerun_change", args=(submission.run_id,)) + "?tab=submissions")
            context["run_review"] = build_run_review(submission)
            from .run_review import current_review_reasons
            context["current_review_reasons"] = current_review_reasons(submission, context["run_review"])
            from .vod_evidence import evidence_presentation
            context["vod"] = evidence_presentation(submission, request.get_host().split(":")[0])
            context["audit_entries"] = submission.audit_entries.select_related("reviewer").all()
            context["audit_outcomes"] = SubmissionAuditEntry.Outcome.choices
            context["can_audit"] = request.user.has_perm("registry.change_runsubmission")
            context["run_queue_url"] = reverse(
                "admin:registry_runsubmission_run_queue", args=(submission.run_id,)
            )
        context["return_to_run"] = request.GET.get("return_to_run") == "1"
        context["run_tab"] = request.GET.get("run_tab") if request.GET.get("run_tab") in {"submissions", "audits"} else ""
        context["review_return_query"] = "return_to_run=1"
        if submission and context["run_tab"]:
            context["run_queue_url"] = reverse("admin:registry_challengerun_change", args=(submission.run_id,)) + "?tab=" + context["run_tab"]
            context["review_return_query"] += "&run_tab=" + context["run_tab"]
        context["decline_error"] = request.GET.get("decline_error", "")
        context["evidence_error"] = request.GET.get("evidence_error", "")
        return super().change_view(request, object_id, form_url, context)

    def get_urls(self):
        return [
            path(
                "run/<uuid:run_id>/",
                self.admin_site.admin_view(self.run_queue_view),
                name="registry_runsubmission_run_queue",
            ),
            path("<uuid:object_id>/audit/", self.admin_site.admin_view(self.audit_view), name="registry_runsubmission_audit"),
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
            path(
                "<path:object_id>/request-evidence/",
                self.admin_site.admin_view(self.request_evidence_view),
                name="registry_runsubmission_request_evidence",
            ),
        ] + super().get_urls()

    def review_submission(self, request, object_id):
        submission = self.get_object(request, object_id)
        if not submission or not self.has_change_permission(request, submission):
            raise Http404
        return submission

    @transaction.atomic
    def audit_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        submission = self.review_submission(request, object_id)
        submission = RunSubmission.objects.select_for_update().get(pk=submission.pk)
        outcome = request.POST.get("outcome", "")
        intervals = request.POST.get("evidence_intervals", "").strip()
        note = request.POST.get("audit_note", "").strip()
        if submission.status != RunSubmission.Status.APPROVED:
            self.message_user(request, "Only accepted submissions can be audited.", level=messages.ERROR)
        elif outcome not in SubmissionAuditEntry.Outcome.values or (
            outcome in ("passed", "action_required") and not note
        ) or (outcome == "passed" and not intervals):
            self.message_user(request, "Choose an audit outcome. Completed audits need a conclusion; passed audits also need the video intervals inspected.", level=messages.ERROR)
        elif len(intervals) > 5000 or len(note) > 5000:
            self.message_user(request, "Keep each audit field within 5,000 characters.", level=messages.ERROR)
        else:
            SubmissionAuditEntry.objects.create(submission=submission, reviewer=request.user,
                outcome=outcome, evidence_intervals=intervals, note=note)
            self.message_user(request, "Audit recorded. Run status and original approval are preserved.", level=messages.SUCCESS)
        return self.redirect_to_review(request, submission)

    def redirect_to_review(self, request, submission):
        if request.GET.get("return_to_run") == "1" and request.GET.get("run_tab") in {"submissions", "audits"}:
            return redirect(reverse("admin:registry_challengerun_change", args=(submission.run_id,)) + "?tab=" + request.GET["run_tab"])
        if request.GET.get("return_to_run") == "1":
            return redirect(
                "admin:registry_runsubmission_run_queue", submission.run_id
            )
        change_url = reverse(
            "admin:registry_runsubmission_change", args=(submission.pk,)
        )
        preserved = request.GET.get("_changelist_filters")
        if preserved:
            from urllib.parse import urlencode

            change_url = f"{change_url}?{urlencode({'_changelist_filters': preserved})}"
        return redirect(change_url)

    def approve_submission_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        submission = self.review_submission(request, object_id)
        from .submission_approval import approve_submission, route_run, ApprovalBlocked
        try:
            submission = approve_submission(submission.pk, request.user)
        except (ApprovalBlocked, OperationalError) as exc:
            if isinstance(exc, OperationalError) and "locked" not in str(exc).lower():
                raise
            error_message = "The database is busy. Approval was not saved. Please try again." if isinstance(exc, OperationalError) else str(exc)
            if isinstance(exc, ApprovalBlocked) and exc.related_run:
                related_url = reverse("admin:registry_challengerun_change", args=(exc.related_run.pk,)) + "?tab=submissions"
                error_message = format_html('{} <a href="{}">Open {} submissions</a>.', error_message, related_url, exc.related_run.character_name or "related run")
            self.message_user(request, error_message, level=messages.ERROR)
            review_url = reverse("admin:registry_runsubmission_change", args=(submission.pk,))
            context_query = []
            if request.GET.get("return_to_run") == "1":
                context_query.append("return_to_run=1")
            if request.GET.get("run_tab") in {"submissions", "audits"}:
                context_query.append("run_tab=" + request.GET["run_tab"])
            return redirect(review_url + ("?" + "&".join(context_query) if context_query else ""))
        else:
            try:
                route_run(submission.run_id)
            except OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                self.message_user(request, "This submission was approved, but the database was busy while checking later submissions. They may still need review.", level=messages.WARNING)
            else:
                self.message_user(request, "The submission was approved.", level=messages.SUCCESS)
        return self.redirect_to_review(request, submission)

    @transaction.atomic
    def decline_submission_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        submission = self.review_submission(request, object_id)
        submission = locked_run_submission_queryset().get(pk=submission.pk)
        run = ChallengeRun.objects.select_for_update().get(pk=submission.run_id)
        if submission.status != RunSubmission.Status.RECEIVED:
            self.message_user(request, "This submission has already been reviewed.", level=messages.WARNING)
            return self.redirect_to_review(request, submission)
        oldest_pending = run.submissions.filter(
            status__in=RunSubmission.moderation_queue_statuses()
        ).order_by("submitted_at", "pk").first()
        if oldest_pending and oldest_pending.pk != submission.pk:
            self.message_user(
                request,
                "Review the run's older pending submission first.",
                level=messages.ERROR,
            )
            return self.redirect_to_review(request, submission)
        reason = request.POST.get("reason", "").strip()
        if not reason:
            change_url = reverse(
                "admin:registry_runsubmission_change", args=(submission.pk,)
            )
            return_to_run = "&return_to_run=1" if request.GET.get("return_to_run") == "1" else ""
            if request.GET.get("run_tab") in {"submissions", "audits"}:
                return_to_run += "&run_tab=" + request.GET["run_tab"]
            return redirect(
                f"{change_url}?decline_error=reason_required{return_to_run}"
            )
        submission.status = RunSubmission.Status.DECLINED
        submission.reviewed_at = timezone.now()
        submission.reviewed_by = request.user
        submission.review_note = reason
        submission.save(
            update_fields=("status", "reviewed_at", "reviewed_by", "review_note")
        )
        latest_pending = run.submissions.filter(
            status__in=RunSubmission.moderation_queue_statuses()
        ).order_by("-event_sequence", "-generated_at").first()
        run.reported_lifecycle_status = (
            latest_pending.reported_lifecycle_status
            if latest_pending
            else run.lifecycle_status
        )
        run.save(update_fields=("reported_lifecycle_status", "updated_at"))
        if run.participant:
            notify(
                run.participant,
                category=Notification.Category.SUBMISSION,
                title="Submission declined",
                message=f"Your Rat Race submission was not approved: {reason}",
                destination=reverse("registry:account"),
            )
        self.message_user(request, "The submission was declined.", level=messages.SUCCESS)
        from .submission_approval import route_run
        transaction.on_commit(lambda run_id=run.pk: route_run(run_id))
        return self.redirect_to_review(request, submission)

    @transaction.atomic
    def request_evidence_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(("POST",))
        submission = self.review_submission(request, object_id)
        submission = locked_run_submission_queryset().get(pk=submission.pk)
        run = ChallengeRun.objects.select_for_update().get(pk=submission.run_id)
        if submission.status != RunSubmission.Status.RECEIVED:
            self.message_user(
                request,
                "Evidence can be requested only for a received submission.",
                level=messages.WARNING,
            )
            return self.redirect_to_review(request, submission)
        oldest_pending = run.submissions.filter(
            status__in=RunSubmission.moderation_queue_statuses()
        ).order_by("submitted_at", "pk").first()
        if oldest_pending and oldest_pending.pk != submission.pk:
            self.message_user(
                request,
                "Resolve the run's older submission first.",
                level=messages.ERROR,
            )
            return self.redirect_to_review(request, submission)
        reason = request.POST.get("reason", "").strip()
        if not reason:
            change_url = reverse(
                "admin:registry_runsubmission_change", args=(submission.pk,)
            )
            return_to_run = (
                "&return_to_run=1" if request.GET.get("return_to_run") == "1" else ""
            )
            if request.GET.get("run_tab") in {"submissions", "audits"}:
                return_to_run += "&run_tab=" + request.GET["run_tab"]
            return redirect(
                f"{change_url}?evidence_error=reason_required{return_to_run}"
            )
        submission.status = RunSubmission.Status.AWAITING_EVIDENCE
        submission.evidence_requested_at = timezone.now()
        submission.evidence_requested_by = request.user
        submission.evidence_request_note = reason
        submission.save(
            update_fields=(
                "status",
                "evidence_requested_at",
                "evidence_requested_by",
                "evidence_request_note",
            )
        )
        if run.participant:
            notify(
                run.participant,
                category=Notification.Category.SUBMISSION,
                title="More evidence needed",
                message=f"A moderator needs more evidence for your submission: {reason}",
                destination=reverse(
                    "registry:update_run_submission_evidence", args=(submission.pk,)
                ),
            )
        self.message_user(
            request,
            "The participant has been asked to update their evidence.",
            level=messages.SUCCESS,
        )
        return self.redirect_to_review(request, submission)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SubmissionAuditStateFilter(admin.SimpleListFilter):
    title = "audit state"
    parameter_name = "audit_state"

    def lookups(self, request, model_admin):
        return [("none", "Not audited"), *SubmissionAuditEntry.Outcome.choices]

    def queryset(self, request, queryset):
        from django.db.models import OuterRef, Subquery
        latest = SubmissionAuditEntry.objects.filter(submission_id=OuterRef("pk")).order_by("-created_at", "-pk")
        queryset = queryset.annotate(latest_audit_state=Subquery(latest.values("outcome")[:1]))
        if self.value() == "none":
            return queryset.filter(latest_audit_state__isnull=True)
        if self.value() in SubmissionAuditEntry.Outcome.values:
            return queryset.filter(latest_audit_state=self.value())
        return queryset


@admin.register(SubmissionAudit)
class SubmissionAuditAdmin(admin.ModelAdmin):
    change_list_template = "admin/registry/submissionaudit/change_list.html"
    list_display = ("run", "submitter", "acceptance", "audit_state", "broadcast_deadline", "reviewed_at", "reviewed_by")
    list_filter = (SubmissionAuditStateFilter, "approval_method", "reviewed_at")
    search_fields = ("run__run_id", "run__character_name", "submitter__nickname")
    actions = None
    list_per_page = 50

    def changelist_view(self, request, extra_context=None):
        from .models import RunSavedView
        view = RunSavedView.objects.filter(system_key="audit").first()
        return redirect(reverse("admin:registry_challengerun_changelist") + (f"?view={view.pk}&reset=1" if view else ""))

    def has_module_permission(self, request):
        return request.user.has_perm("registry.view_runsubmission")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("registry.view_runsubmission")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("registry.change_runsubmission")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).filter(status="approved").select_related(
            "run", "submitter", "reviewed_by").prefetch_related("audit_entries")

    @admin.display(description="Approval")
    def acceptance(self, obj):
        return obj.moderator_status

    @admin.display(description="Audit")
    def audit_state(self, obj):
        entry = next(iter(obj.audit_entries.all()), None)
        return entry.get_outcome_display() if entry else "Not audited"

    @admin.display(description="VOD audit deadline")
    def broadcast_deadline(self, obj):
        from .vod_evidence import evidence_presentation
        evidence = evidence_presentation(obj, "localhost")
        if not evidence["deadline"]:
            return "Broadcast date unknown"
        return evidence["deadline"].strftime("%d %b %Y %H:%M UTC") + (" (elapsed)" if evidence["expired"] else "")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if not self.has_view_permission(request):
            raise Http404
        return redirect("admin:registry_runsubmission_change", object_id)
