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
from django.db.models import Case, IntegerField, Value, When
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import (
    AccountClosureRecord,
    ChallengeMode,
    ChallengeModeAlias,
    ChallengeRun,
    LegacyDataImport,
    LegacyRun,
    LegacyRunClaim,
    LegacyRunSubmission,
    Notification,
    Participant,
    RunSubmission,
    StreamingAccount,
    StreamingMedia,
    WorkshopMod,
    WorkshopModVote,
)
from .legacy_imports import apply_legacy_import, create_legacy_import_review
from .legacy_submissions import legacy_submission_strength


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
from .run_review import build_run_review
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
        "display_name", "key", "game_mode_name", "max_active_runs_per_participant",
        "is_active", "display_order",
    )
    list_editable = ("max_active_runs_per_participant", "is_active", "display_order")
    search_fields = ("display_name", "key", "game_mode_name", "aliases__key")
    inlines = (ChallengeModeAliasInline,)


@admin.register(ChallengeRun)
class ChallengeRunAdmin(admin.ModelAdmin):
    list_display = (
        "run_id", "participant", "character_name", "challenge_mode", "lifecycle_status", "status",
        "current_kills", "event_sequence", "updated_at",
    )
    list_filter = (
        "challenge_mode", "lifecycle_status", "status", "export_format", "bootstrapped", "updated_at"
    )
    search_fields = ("run_id", "character_name", "participant__nickname", "participant__email")
    readonly_fields = (
        "participant", "status", "approved_submission", "challenge_mode",
        "challenge_id", "challenge_game_mode",
        "starting_challenge_mode", "starting_challenge_id",
        "starting_challenge_game_mode",
        "run_id", "export_format", "generated_at", "current_kills",
        "event_sequence", "event_hash", "character_name", "bootstrapped",
        "latest_projection", "latest_events", "participant_deactivated_at",
        "first_submitted_at", "updated_at",
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
        "challenge_mode", "challenge_id", "challenge_game_mode",
        "submitted_at", "evidence_provider", "evidence_media_type",
        "evidence_media_id", "evidence_url", "evidence_title",
        "evidence_start_seconds", "evidence_end_seconds", "evidence_clips",
        "projection", "reviewed_at", "review_note",
    )

    class Media:
        css = {"all": ("registry/admin_run_review.css",)}

    def changelist_view(self, request, extra_context=None):
        context = dict(extra_context or {})
        context["title"] = "Run submission reviews"
        return super().changelist_view(request, extra_context=context)

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
        starting_challenge_id = submission.run.starting_challenge_id
        expected_challenge_id = (
            baseline.challenge_id if baseline and baseline.challenge_id else starting_challenge_id
        )
        if (
            expected_challenge_id
            and submission.challenge_id
            and expected_challenge_id != submission.challenge_id
        ):
            self.message_user(
                request,
                "This submission reports a different challenge mode from the approved baseline.",
                level=messages.ERROR,
            )
            return redirect("admin:registry_runsubmission_change", submission.pk)
        if baseline:
            if submission.event_sequence < baseline.event_sequence:
                self.message_user(
                    request,
                    "This submission is older than the current approved snapshot.",
                    level=messages.ERROR,
                )
                return redirect("admin:registry_runsubmission_change", submission.pk)
            if submission.event_sequence == baseline.event_sequence:
                if submission.event_hash != baseline.event_hash:
                    self.message_user(
                        request,
                        "This submission conflicts with the current approved ledger.",
                        level=messages.ERROR,
                    )
                    return redirect("admin:registry_runsubmission_change", submission.pk)
                if submission.generated_at <= baseline.generated_at:
                    self.message_user(
                        request,
                        "This submission is not newer than the current approved snapshot.",
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
        run.challenge_mode = resolve_challenge_mode(
            decoded.challenge_id, decoded.challenge_game_mode
        )
        run.challenge_id = decoded.challenge_id
        run.challenge_game_mode = decoded.challenge_game_mode
        run.export_format = decoded.format
        run.generated_at = decoded.generated_at
        run.current_kills = decoded.current_kills
        run.event_sequence = decoded.event_sequence
        run.event_hash = decoded.event_hash
        run.character_name = decoded.character_name
        run.bootstrapped = decoded.bootstrapped
        run.latest_projection = decoded.projection
        run.latest_events = decoded.events
        if decoded.lifecycle == ChallengeRun.Lifecycle.DECEASED:
            run.lifecycle_status = ChallengeRun.Lifecycle.DECEASED
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
