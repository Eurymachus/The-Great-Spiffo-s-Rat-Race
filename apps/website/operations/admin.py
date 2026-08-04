from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from zomboid_catalogue.models import (
    CatalogueAsset,
    CatalogueEntry,
    ItemDisplayCategory,
    ItemDetails,
    OccupationDetails,
    SkillDetails,
    TraitDetails,
)

from .catalogue_review import approve_catalogue_review
from .models import (
    CatalogueImportReview,
    PZWikiArtworkSyncJob,
    ReferenceSource,
    ReferenceUpdateJob,
    RunDataDangerZone,
)
from .pzwiki_artwork import enqueue_pzwiki_artwork_sync
from .queue import enqueue_reference_update
from .steam_auth import (
    begin_authentication,
    complete_authentication,
    poll_authentication,
)


class ConnectSteamForm(forms.Form):
    account_name = forms.CharField(max_length=80, label="Steam account login name")
    steam_password = forms.CharField(widget=forms.PasswordInput, strip=False)
    admin_password = forms.CharField(
        widget=forms.PasswordInput,
        strip=False,
        label="Confirm your Rat Race administrator password",
    )


class SteamGuardForm(forms.Form):
    guard_code = forms.CharField(max_length=12, label="Steam Guard code")

    def clean_guard_code(self):
        code = self.cleaned_data["guard_code"].strip()
        if not code.isalnum():
            raise forms.ValidationError("Enter the Steam Guard code exactly as shown.")
        return code


class CatalogueDryRunForm(forms.Form):
    game_version = forms.CharField(
        max_length=32,
        label="Project Zomboid version",
        help_text="The catalogue version label to review, for example 42.19.",
    )


class PurgeRunDataForm(forms.Form):
    confirmation = forms.CharField(
        label='Type "DELETE ALL RUN DATA" to confirm',
        strip=True,
    )

    def clean_confirmation(self):
        confirmation = self.cleaned_data["confirmation"]
        if confirmation != "DELETE ALL RUN DATA":
            raise forms.ValidationError("The confirmation text did not match.")
        return confirmation


@admin.register(RunDataDangerZone)
class RunDataDangerZoneAdmin(admin.ModelAdmin):
    change_list_template = "admin/operations/run_data_danger_zone.html"

    def changelist_view(self, request, extra_context=None):
        if not request.user.is_superuser:
            return HttpResponseForbidden()

        from registry.models import ChallengeRun, Notification, RunSubmission

        counts = {
            "runs": ChallengeRun.objects.count(),
            "submissions": RunSubmission.objects.count(),
            "notifications": Notification.objects.filter(
                category=Notification.Category.SUBMISSION
            ).count(),
        }
        form = PurgeRunDataForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            with transaction.atomic():
                deleted_notifications, _ = Notification.objects.filter(
                    category=Notification.Category.SUBMISSION
                ).delete()
                ChallengeRun.objects.all().delete()
            messages.success(
                request,
                (
                    "Run data purged: "
                    f"{counts['runs']} runs, {counts['submissions']} submissions, "
                    f"and {deleted_notifications} submission notifications removed."
                ),
            )
            return redirect("admin:operations_rundatadangerzone_changelist")

        context = {
            **self.admin_site.each_context(request),
            "title": "Run data danger zone",
            "opts": self.model._meta,
            "form": form,
            "counts": counts,
        }
        return TemplateResponse(request, self.change_list_template, context)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReferenceSource)
class ReferenceSourceAdmin(admin.ModelAdmin):
    change_list_template = "admin/operations/change_list.html"
    list_display = (
        "name",
        "authentication_status",
        "installed_build_id",
        "decompiled_build_id",
        "decompilation_status",
        "last_checked_at",
        "last_updated_at",
    )
    fields = (
        "name",
        "app_id",
        "authentication_status",
        "account_name",
        "steamcmd_path",
        "install_root",
        "authenticated_at",
        "installed_build_id",
        "decompiled_build_id",
        "decompiled_at",
        "decompilation_status",
        "java_executable",
        "decompiler_jar",
        "decompiled_root",
        "last_checked_at",
        "last_updated_at",
        "last_error",
        "connection_action",
        "update_action",
        "decompile_action",
        "catalogue_action",
        "pzwiki_action",
    )
    readonly_fields = (
        "name",
        "app_id",
        "authentication_status",
        "authenticated_at",
        "installed_build_id",
        "decompiled_build_id",
        "decompiled_at",
        "decompiled_root",
        "decompilation_status",
        "last_checked_at",
        "last_updated_at",
        "last_error",
        "connection_action",
        "update_action",
        "decompile_action",
        "catalogue_action",
        "pzwiki_action",
    )

    def get_urls(self):
        return [
            path(
                "<path:object_id>/connect/",
                self.admin_site.admin_view(self.connect_view),
                name="operations_referencesource_connect",
            ),
            path(
                "<path:object_id>/guard/",
                self.admin_site.admin_view(self.guard_view),
                name="operations_referencesource_guard",
            ),
            path(
                "<path:object_id>/check-for-updates/",
                self.admin_site.admin_view(self.check_for_updates_view),
                name="operations_referencesource_check_updates",
            ),
            path(
                "<path:object_id>/decompile/",
                self.admin_site.admin_view(self.decompile_view),
                name="operations_referencesource_decompile",
            ),
            path(
                "<path:object_id>/catalogue-dry-run/",
                self.admin_site.admin_view(self.catalogue_dry_run_view),
                name="operations_referencesource_catalogue_dry_run",
            ),
            path(
                "<path:object_id>/sync-pzwiki-artwork/",
                self.admin_site.admin_view(self.sync_pzwiki_artwork_view),
                name="operations_referencesource_sync_pzwiki_artwork",
            ),
            *super().get_urls(),
        ]

    @admin.display(description="Steam connection")
    def connection_action(self, obj):
        if not obj or not obj.pk:
            return "Save the source configuration first."
        url = reverse("admin:operations_referencesource_connect", args=(obj.pk,))
        label = "Reconnect Steam" if obj.authenticated_at else "Connect Steam"
        return format_html('<a class="button" href="{}">{}</a>', url, label)

    @admin.display(description="Reference update")
    def update_action(self, obj):
        if not obj or not obj.pk:
            return "Save the source configuration first."
        url = reverse(
            "admin:operations_referencesource_check_updates", args=(obj.pk,)
        )
        return format_html('<a class="button" href="{}">Check for updates</a>', url)

    @admin.display(description="Decompiled Java reference")
    def decompile_action(self, obj):
        if not obj or not obj.pk:
            return "Save the source configuration first."
        url = reverse("admin:operations_referencesource_decompile", args=(obj.pk,))
        if obj.installed_build_id == obj.decompiled_build_id:
            label = "Rebuild decompiled reference"
        else:
            label = "Decompile installed build"
        return format_html('<a class="button" href="{}">{}</a>', url, label)

    @admin.display(description="Catalogue")
    def catalogue_action(self, obj):
        if not obj or not obj.pk:
            return "Save the source configuration first."
        if (
            not obj.installed_build_id
            or obj.installed_build_id != obj.decompiled_build_id
            or not obj.decompiled_root
        ):
            return "Update and decompile the installed build first."
        url = reverse(
            "admin:operations_referencesource_catalogue_dry_run", args=(obj.pk,)
        )
        return format_html('<a class="button" href="{}">Generate catalogue review</a>', url)

    @admin.display(description="PZWiki artwork")
    def pzwiki_action(self, obj):
        if not obj or not obj.pk:
            return "Save the source configuration first."
        review = (
            CatalogueImportReview.objects.filter(
                source=obj,
                status=CatalogueImportReview.Status.APPROVED,
            )
            .order_by("-reviewed_at", "-pk")
            .first()
        )
        if not review:
            return "Approve a catalogue review first."
        url = reverse(
            "admin:operations_referencesource_sync_pzwiki_artwork",
            args=(obj.pk,),
        )
        return format_html('<a class="button" href="{}">Sync PZWiki artwork</a>', url)

    @admin.display(description="Decompilation status")
    def decompilation_status(self, obj):
        if not obj or not obj.installed_build_id:
            return "Install or check Project Zomboid first."
        if obj.installed_build_id == obj.decompiled_build_id:
            return f"Current for build {obj.installed_build_id}"
        if obj.decompiled_build_id:
            return (
                f"Required: installed build {obj.installed_build_id}; "
                f"decompiled build {obj.decompiled_build_id}"
            )
        return f"Required for installed build {obj.installed_build_id}"

    def check_for_updates_view(self, request, object_id):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        source = get_object_or_404(ReferenceSource, pk=object_id)
        if request.method == "POST":
            job, created = enqueue_reference_update(
                source,
                trigger=ReferenceUpdateJob.Trigger.MANUAL,
                requested_by=request.user,
            )
            if created:
                messages.success(
                    request,
                    f"Project Zomboid reference update #{job.pk} was queued.",
                )
            else:
                messages.warning(
                    request,
                    f"Update #{job.pk} is already {job.get_status_display().lower()}.",
                )
            return redirect("admin:operations_referenceupdatejob_change", job.pk)
        return TemplateResponse(
            request,
            "admin/operations/check_reference_update.html",
            {
                **self.admin_site.each_context(request),
                "title": "Check Project Zomboid for updates",
                "source": source,
                "opts": self.model._meta,
            },
        )

    def decompile_view(self, request, object_id):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        source = get_object_or_404(ReferenceSource, pk=object_id)
        if request.method == "POST":
            job, created = enqueue_reference_update(
                source,
                operation=ReferenceUpdateJob.Operation.DECOMPILE,
                trigger=ReferenceUpdateJob.Trigger.MANUAL,
                requested_by=request.user,
            )
            if created:
                messages.success(
                    request,
                    f"Project Zomboid decompilation #{job.pk} was queued.",
                )
            else:
                messages.warning(
                    request,
                    f"Decompilation #{job.pk} is already "
                    f"{job.get_status_display().lower()}.",
                )
            return redirect("admin:operations_referenceupdatejob_change", job.pk)
        return TemplateResponse(
            request,
            "admin/operations/decompile_reference.html",
            {
                **self.admin_site.each_context(request),
                "title": "Decompile Project Zomboid reference",
                "source": source,
                "opts": self.model._meta,
            },
        )

    def catalogue_dry_run_view(self, request, object_id):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        source = get_object_or_404(ReferenceSource, pk=object_id)
        if (
            not source.installed_build_id
            or source.installed_build_id != source.decompiled_build_id
            or not source.decompiled_root
        ):
            messages.error(request, "Update and decompile the installed build first.")
            return redirect("admin:operations_referencesource_change", source.pk)
        form = CatalogueDryRunForm(request.POST or None, initial={"game_version": "42.19"})
        if request.method == "POST" and form.is_valid():
            review = CatalogueImportReview.objects.create(
                source=source,
                status=CatalogueImportReview.Status.QUEUED,
                game_version=form.cleaned_data["game_version"].strip(),
                installed_build_id=source.installed_build_id,
                decompiled_build_id=source.decompiled_build_id,
                install_root=source.install_root,
                decompiled_root=source.decompiled_root,
                requested_by=request.user,
            )
            messages.success(request, f"Catalogue review #{review.pk} was queued.")
            return redirect("admin:operations_catalogueimportreview_change", review.pk)
        return TemplateResponse(
            request,
            "admin/operations/catalogue_dry_run.html",
            {
                **self.admin_site.each_context(request),
                "title": "Generate catalogue review",
                "source": source,
                "form": form,
                "opts": self.model._meta,
            },
        )

    def sync_pzwiki_artwork_view(self, request, object_id):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        source = get_object_or_404(ReferenceSource, pk=object_id)
        review = (
            CatalogueImportReview.objects.filter(
                source=source,
                status=CatalogueImportReview.Status.APPROVED,
            )
            .order_by("-reviewed_at", "-pk")
            .first()
        )
        if not review:
            messages.error(request, "Approve a catalogue review first.")
            return redirect("admin:operations_referencesource_change", source.pk)
        if request.method == "POST":
            job, created = enqueue_pzwiki_artwork_sync(
                catalogue_review=review,
                trigger=PZWikiArtworkSyncJob.Trigger.MANUAL,
                requested_by=request.user,
            )
            if not created:
                messages.warning(
                    request,
                    f"PZWiki artwork sync job #{job.pk} is already "
                    f"{job.get_status_display().lower()}.",
                )
            else:
                messages.success(
                    request, f"PZWiki artwork sync job #{job.pk} was queued."
                )
            return redirect(
                "admin:operations_pzwikiartworksyncjob_change", job.pk
            )
        return TemplateResponse(
            request,
            "admin/operations/sync_pzwiki_artwork.html",
            {
                **self.admin_site.each_context(request),
                "title": "Sync PZWiki catalogue artwork",
                "source": source,
                "review": review,
                "opts": self.model._meta,
            },
        )

    def connect_view(self, request, object_id):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        source = get_object_or_404(ReferenceSource, pk=object_id)
        initial = {"account_name": source.account_name}
        form = ConnectSteamForm(request.POST or None, initial=initial)
        if request.method == "POST" and form.is_valid():
            rate_key = f"steam-auth:{request.user.pk}"
            attempts = cache.get(rate_key, 0)
            if attempts >= 5:
                form.add_error(None, "Too many attempts. Try again in 15 minutes.")
            elif not request.user.check_password(form.cleaned_data["admin_password"]):
                cache.set(rate_key, attempts + 1, 900)
                form.add_error("admin_password", "Your administrator password is incorrect.")
            else:
                executable = source.steamcmd_path or settings.STEAMCMD_EXECUTABLE
                if not executable or not Path(executable).is_file():
                    form.add_error(None, "Configure a valid SteamCMD executable first.")
                else:
                    try:
                        status, token = begin_authentication(
                            executable,
                            form.cleaned_data["account_name"],
                            form.cleaned_data["steam_password"],
                        )
                    except Exception:
                        status, token = "failed", ""
                    if status == "authenticated":
                        self._mark_authenticated(source, form.cleaned_data["account_name"])
                        cache.delete(rate_key)
                        messages.success(request, "Steam authentication completed.")
                        return redirect("admin:operations_referencesource_change", source.pk)
                    if status == "guard_required":
                        request.session["steam_guard_attempt"] = token
                        request.session["steam_guard_source"] = source.pk
                        request.session["steam_guard_account"] = form.cleaned_data["account_name"]
                        return redirect("admin:operations_referencesource_guard", source.pk)
                    cache.set(rate_key, attempts + 1, 900)
                    form.add_error(None, "Steam rejected the authentication attempt.")
        return self._form_response(request, source, form, "Connect Steam")

    def guard_view(self, request, object_id):
        if not request.user.is_superuser:
            return HttpResponseForbidden()
        source = get_object_or_404(ReferenceSource, pk=object_id)
        if request.session.get("steam_guard_source") != source.pk:
            messages.error(request, "The Steam authentication attempt has expired.")
            return redirect("admin:operations_referencesource_connect", source.pk)
        if request.method == "POST" and request.POST.get("_poll") == "1":
            status = poll_authentication(
                request.session.get("steam_guard_attempt", "")
            )
            if status == "authenticated":
                account_name = request.session.pop("steam_guard_account", "")
                request.session.pop("steam_guard_attempt", None)
                request.session.pop("steam_guard_source", None)
                self._mark_authenticated(source, account_name)
                return JsonResponse(
                    {
                        "status": "authenticated",
                        "redirect": reverse(
                            "admin:operations_referencesource_change",
                            args=(source.pk,),
                        ),
                    }
                )
            return JsonResponse({"status": status})
        form = SteamGuardForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            executable = source.steamcmd_path or settings.STEAMCMD_EXECUTABLE
            try:
                success = complete_authentication(
                    executable,
                    request.session.pop("steam_guard_attempt", ""),
                    form.cleaned_data["guard_code"],
                )
            except Exception:
                success = False
            account_name = request.session.pop("steam_guard_account", "")
            request.session.pop("steam_guard_source", None)
            if success:
                self._mark_authenticated(source, account_name)
                messages.success(request, "Steam Guard authentication completed.")
                return redirect("admin:operations_referencesource_change", source.pk)
            form.add_error("guard_code", "Steam rejected that code. Start again.")
        return self._form_response(
            request,
            source,
            form,
            "Complete Steam Guard",
            poll_for_approval=True,
        )

    def _form_response(
        self, request, source, form, title, poll_for_approval=False
    ):
        return TemplateResponse(
            request,
            "admin/operations/steam_auth.html",
            {
                **self.admin_site.each_context(request),
                "title": title,
                "source": source,
                "form": form,
                "opts": self.model._meta,
                "poll_for_approval": poll_for_approval,
            },
        )

    @staticmethod
    def _mark_authenticated(source, account_name):
        source.account_name = account_name
        source.authentication_status = ReferenceSource.AuthenticationStatus.AUTHENTICATED
        source.authenticated_at = timezone.now()
        source.last_error = ""
        source.save(
            update_fields=(
                "account_name",
                "authentication_status",
                "authenticated_at",
                "last_error",
            )
        )

    def has_add_permission(self, request):
        return not ReferenceSource.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReferenceUpdateJob)
class ReferenceUpdateJobAdmin(admin.ModelAdmin):
    change_list_template = "admin/operations/change_list.html"
    list_display = (
        "source", "operation", "status", "trigger", "requested_by", "requested_at",
        "started_at", "finished_at",
    )
    readonly_fields = (
        "source", "operation", "status", "trigger", "requested_by", "previous_build_id",
        "installed_build_id", "requested_at", "started_at", "finished_at", "summary",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CatalogueImportReview)
class CatalogueImportReviewAdmin(admin.ModelAdmin):
    change_form_template = "admin/operations/catalogueimportreview/change_form.html"
    change_list_template = "admin/operations/catalogueimportreview/change_list.html"
    list_display = (
        "id", "source", "game_version", "installed_build_id", "status",
        "requested_by", "requested_at", "reviewed_by", "reviewed_at",
    )
    readonly_fields = (
        "source", "status", "game_version", "installed_build_id",
        "decompiled_build_id", "install_root", "decompiled_root", "requested_by",
        "requested_at", "started_at", "finished_at", "reviewed_by", "reviewed_at",
        "summary", "affected_catalogue_display", "diff_display",
    )
    fields = readonly_fields

    def get_urls(self):
        return [
            path(
                "<path:object_id>/approve/",
                self.admin_site.admin_view(self.approve_view),
                name="operations_catalogueimportreview_approve",
            ),
            path(
                "<path:object_id>/reject/",
                self.admin_site.admin_view(self.reject_view),
                name="operations_catalogueimportreview_reject",
            ),
            *super().get_urls(),
        ]

    @admin.display(description="Proposed catalogue changes")
    def diff_display(self, obj):
        if not obj or not obj.diff:
            return "The review has not produced a comparison yet."
        sections = []
        labels = (("added", "Add"), ("changed", "Change"), ("removed", "Deactivate"))
        for key, label in labels:
            rows = obj.diff.get(key, [])
            items = "".join(
                f"<li><strong>{row['display_name']}</strong> "
                f"({row['kind']}: {row['stable_id']})"
                f"{' — ' + ', '.join(row.get('fields', [])) if row.get('fields') else ''}</li>"
                for row in rows
            ) or "<li>None</li>"
            sections.append(f"<h3>{label} ({len(rows)})</h3><ul>{items}</ul>")
        return format_html("".join(sections))

    @admin.display(description="Affected catalogue tables")
    def affected_catalogue_display(self, obj):
        if not obj or not obj.snapshot:
            return "The review has not produced a catalogue snapshot yet."

        kind_counts = {
            kind: sum(1 for row in obj.snapshot if row.get("kind") == kind)
            for kind in (
                CatalogueEntry.Kind.TRAIT,
                CatalogueEntry.Kind.OCCUPATION,
                CatalogueEntry.Kind.SKILL,
                CatalogueEntry.Kind.ITEM,
            )
        }
        changed_rows = (obj.diff or {}).get("changed", [])
        changed_by_kind = {
            kind: sum(1 for row in changed_rows if row.get("kind") == kind)
            for kind in kind_counts
        }
        tables = [
            (
                "Catalogue entries",
                len(obj.snapshot),
                len(changed_rows),
                CatalogueEntry._meta.db_table,
            ),
            (
                "Trait details",
                kind_counts[CatalogueEntry.Kind.TRAIT],
                changed_by_kind[CatalogueEntry.Kind.TRAIT],
                TraitDetails._meta.db_table,
            ),
            (
                "Occupation details",
                kind_counts[CatalogueEntry.Kind.OCCUPATION],
                changed_by_kind[CatalogueEntry.Kind.OCCUPATION],
                OccupationDetails._meta.db_table,
            ),
            (
                "Skill details",
                kind_counts[CatalogueEntry.Kind.SKILL],
                changed_by_kind[CatalogueEntry.Kind.SKILL],
                SkillDetails._meta.db_table,
            ),
            (
                "Item details",
                kind_counts[CatalogueEntry.Kind.ITEM],
                changed_by_kind[CatalogueEntry.Kind.ITEM],
                ItemDetails._meta.db_table,
            ),
        ]
        item_categories = {
            row.get("details", {}).get("display_category_stable_id")
            for row in obj.snapshot
            if row.get("kind") == CatalogueEntry.Kind.ITEM
            and row.get("details", {}).get("display_category_stable_id")
        }
        if item_categories:
            tables.append(
                (
                    "Item display categories",
                    len(item_categories),
                    "—",
                    ItemDisplayCategory._meta.db_table,
                )
            )
        asset_count = sum(1 for row in obj.snapshot if row.get("asset"))
        if asset_count:
            tables.append(
                ("Catalogue assets", asset_count, "—", CatalogueAsset._meta.db_table)
            )

        table_rows = format_html_join(
            "",
            "<tr><th>{}</th><td>{}</td><td>{}</td><td><code>{}</code></td></tr>",
            tables,
        )
        diff = obj.diff or {}
        return format_html(
            "<p>Approval applies this reviewed snapshot to the catalogue tables "
            "below. Records absent from the reviewed game version are deactivated.</p>"
            "<table><thead><tr><th>Admin section</th><th>Reviewed records</th>"
            "<th>Changed</th><th>Database table</th></tr></thead>"
            "<tbody>{}</tbody></table>"
            "<p><small>Asset files are applied from the approved snapshot and are "
            "not counted separately as catalogue record changes.</small></p>"
            "<p><strong>Proposed changes:</strong> {} added, {} changed, "
            "{} deactivated.</p>",
            table_rows,
            len(diff.get("added", [])),
            len(diff.get("changed", [])),
            len(diff.get("removed", [])),
        )

    def approve_view(self, request, object_id):
        if not request.user.is_superuser or request.method != "POST":
            return HttpResponseForbidden()
        review = get_object_or_404(CatalogueImportReview, pk=object_id)
        try:
            review = approve_catalogue_review(review, request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            if review.status == CatalogueImportReview.Status.STALE:
                messages.error(
                    request,
                    "The Project Zomboid reference changed; generate a new catalogue review.",
                )
            else:
                messages.success(
                    request,
                    "The reviewed catalogue snapshot was approved and applied.",
                )
        return redirect("admin:operations_catalogueimportreview_change", review.pk)

    def reject_view(self, request, object_id):
        if not request.user.is_superuser or request.method != "POST":
            return HttpResponseForbidden()
        review = get_object_or_404(CatalogueImportReview, pk=object_id)
        if review.status != CatalogueImportReview.Status.READY:
            messages.error(request, "Only a ready catalogue review can be rejected.")
        else:
            review.status = CatalogueImportReview.Status.REJECTED
            review.reviewed_by = request.user
            review.reviewed_at = timezone.now()
            review.save(update_fields=("status", "reviewed_by", "reviewed_at"))
            messages.success(request, "The catalogue review was rejected without changing the catalogue.")
        return redirect("admin:operations_catalogueimportreview_change", review.pk)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PZWikiArtworkSyncJob)
class PZWikiArtworkSyncJobAdmin(admin.ModelAdmin):
    change_list_template = "admin/operations/change_list.html"
    list_display = (
        "id",
        "source",
        "catalogue_review",
        "status",
        "trigger",
        "requested_by",
        "requested_at",
        "started_at",
        "finished_at",
        "unavailable_count",
    )
    list_filter = ("status", "trigger", "source")
    readonly_fields = (
        "source",
        "catalogue_review",
        "status",
        "trigger",
        "requested_by",
        "requested_at",
        "started_at",
        "finished_at",
        "summary",
        "unavailable_artwork_display",
    )
    fields = readonly_fields

    @admin.display(description="Unavailable")
    def unavailable_count(self, obj):
        return len(obj.unavailable_artwork or [])

    @admin.display(description="Unavailable artwork")
    def unavailable_artwork_display(self, obj):
        rows = obj.unavailable_artwork or []
        if not rows:
            if obj.status == PZWikiArtworkSyncJob.Status.COMPLETE:
                return "No unavailable artwork was recorded."
            return "The report will be available after this job completes."

        reason_labels = {
            "no_supported_icon_key": "No supported icon key",
            "no_infobox_artwork_on_pzwiki": (
                "No representative artwork found on the PZWiki page"
            ),
            "not_found_on_pzwiki": "Expected file not found on PZWiki",
            "pzwiki_download_failed": "PZWiki download failed after retries",
        }
        reason_counts = {}
        kind_counts = {}
        for row in rows:
            reason = row.get("reason", "unknown")
            kind = row.get("kind", "unknown")
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            kind_counts[kind] = kind_counts.get(kind, 0) + 1

        summary = format_html_join(
            ", ",
            "<strong>{}</strong> {}",
            (
                (count, reason_labels.get(reason, reason.replace("_", " ")))
                for reason, count in sorted(reason_counts.items())
            ),
        )
        kinds = format_html_join(
            ", ",
            "<strong>{}</strong> {}",
            ((count, kind) for kind, count in sorted(kind_counts.items())),
        )
        table_rows = format_html_join(
            "",
            (
                "<tr><td>{}</td><td>{}</td><td><code>{}</code></td>"
                "<td><code>{}</code></td><td><code>{}</code></td><td>{}</td></tr>"
            ),
            (
                (
                    row.get("kind", ""),
                    row.get("display_name", ""),
                    row.get("stable_id", ""),
                    row.get("icon_key", "") or "-",
                    row.get("expected_filename", "") or "-",
                    reason_labels.get(
                        row.get("reason", ""),
                        row.get("reason", "").replace("_", " "),
                    ),
                )
                for row in rows
            ),
        )
        return format_html(
            "<p><strong>{} unavailable.</strong> {}.</p>"
            "<p>By catalogue kind: {}.</p>"
            "<details><summary>Show all unavailable artwork</summary>"
            "<div style=\"overflow-x:auto; margin-top:0.75rem\">"
            "<table><thead><tr><th>Kind</th><th>Entry</th><th>Stable ID</th>"
            "<th>Icon key</th><th>Expected PZWiki file</th><th>Reason</th>"
            "</tr></thead><tbody>{}</tbody></table></div></details>",
            len(rows),
            summary,
            kinds,
            table_rows,
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False
