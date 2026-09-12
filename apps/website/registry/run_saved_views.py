"""Personal and shared filters for the run moderation workspace."""
from datetime import timedelta
from django.db import transaction
from django.db.models import Q, Exists, OuterRef, Subquery
from django.http import QueryDict, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import RunSavedView, RunViewPreference, RunWorkspacePreference, RunSubmission, SubmissionAuditEntry

FILTERS = ("q", "challenge_mode", "lifecycle_status", "status", "export_format", "bootstrapped", "updated", "work", "audit", "vod", "sort")
CHOICES = {
    "work": {"", "review", "evidence"},
    "audit": {"", "unaudited", "selected", "in_progress", "action_required"},
    "vod": {"", "closing", "unknown", "expired"},
    "sort": {'', 'character_name', '-event_sequence', '-updated_at', 'participant__nickname', '-character_name', '-lifecycle_status', 'status', '-submission_count', 'lifecycle_status', 'submission_count', 'event_sequence', 'updated_at', '-current_kills', '-participant__nickname', 'current_kills', '-status'},
}


def clean_filters(data):
    result = {key: str(data.get(key, ""))[:200] for key in FILTERS}
    for key, choices in CHOICES.items():
        if key == "sort":
            if result[key] not in choices:
                result[key] = ""
        else:
            result[key] = ",".join(dict.fromkeys(value for value in result[key].split(",") if value and value in choices))
    mode = result["challenge_mode"]
    result["challenge_mode"] = ",".join(dict.fromkeys(value for value in mode.split(",") if value == "unmapped" or value.isdigit()))
    return result


def available(user):
    return RunSavedView.objects.filter(Q(shared=True) | Q(owner=user))


def preferences(user):
    existing = set(RunViewPreference.objects.filter(user=user).values_list("view_id", flat=True))
    position = max(RunViewPreference.objects.filter(user=user).values_list("position", flat=True), default=-1) + 1
    for view in available(user):
        if view.pk not in existing:
            RunViewPreference.objects.get_or_create(user=user, view=view, defaults={"position": position})
            position += 1
    return list(RunViewPreference.objects.filter(user=user, view__in=available(user)).select_related("view").order_by("position", "pk"))


def resolve_view(request):
    prefs = preferences(request.user)
    visible = [p for p in prefs if not p.hidden]
    if not visible and prefs:
        prefs[0].hidden = False
        prefs[0].save(update_fields=("hidden",))
        visible = [prefs[0]]
    workspace, _ = RunWorkspacePreference.objects.get_or_create(user=request.user)
    selected = next((p for p in visible if str(p.view_id) == request.GET.get("view")), None)
    if not selected and "view" not in request.GET:
        selected = next((p for p in visible if p.view_id == workspace.last_view_id), None)
    selected = selected or next((p for p in visible if p.view.system_key == "review"), None) or (visible[0] if visible else None)
    params = QueryDict(mutable=True)
    if selected:
        params.update(clean_filters(selected.filters or selected.view.filters))
        if "reset" in request.GET:
            params = QueryDict(mutable=True)
            params.update(clean_filters(selected.view.filters))
    for key in FILTERS:
        if key in request.GET:
            params[key] = request.GET[key]
    for key, value in clean_filters(params).items():
        params[key] = value
    if selected:
        params["view"] = str(selected.view_id)
        selected.filters = clean_filters(params)
        selected.save(update_fields=("filters",))
        workspace.last_view = selected.view
        workspace.save(update_fields=("last_view",))
    params["page"] = request.GET.get("page", "1")
    return params, {
        "saved_tabs": visible, "managed_tabs": prefs, "selected_view": selected.view if selected else None,
        "can_edit_view": bool(selected and (request.user.has_perm("registry.manage_shared_run_views") if selected.view.shared else selected.view.owner_id == request.user.pk)),
        "can_share_views": request.user.has_perm("registry.manage_shared_run_views"),
        "saved_filter_fields": list(clean_filters(params).items()),
        "selected_work": params.get("work", ""), "selected_audit": params.get("audit", ""),
        "selected_vod": params.get("vod", ""), "selected_sort": params.get("sort", ""),
    }


@transaction.atomic
def manage_view(request):
    if not request.user.has_perm("registry.view_challengerun"):
        raise Http404
    action = request.POST.get("action")
    view_id = request.POST.get("view", "")
    view = available(request.user).filter(pk=view_id if view_id.isdigit() else None).first()
    can_share = request.user.has_perm("registry.manage_shared_run_views")
    can_edit = view and (can_share if view.shared else view.owner_id == request.user.pk)
    url = reverse("admin:registry_challengerun_changelist")
    prefs = preferences(request.user)
    pref = next((p for p in prefs if view and p.view_id == view.pk), None)
    if action in {"create", "update"}:
        if action == "update" and not can_edit:
            raise Http404
        shared = request.POST.get("shared") == "on"
        if shared and not can_share:
            raise Http404
        name = request.POST.get("name", "").strip()[:80]
        if not name:
            from django.contrib import messages
            messages.error(request, "Give the view a name.")
            return redirect(url)
        if action == "create":
            view = RunSavedView(owner=request.user)
        view.name, view.shared, view.filters = name, shared, clean_filters(request.POST)
        view.save()
        # A shared edit takes effect for everyone, including their remembered overrides.
        RunViewPreference.objects.filter(view=view).update(filters={})
        RunViewPreference.objects.get_or_create(user=request.user, view=view, defaults={"position": len(prefs)})
        return redirect(url + "?view=" + str(view.pk) + "&reset=1")
    if action == "delete":
        if not can_edit or view.system_key:
            raise Http404
        view.delete()
    elif action in {"hide", "show"} and pref:
        if action == "hide" and sum(not p.hidden for p in prefs) <= 1:
            from django.contrib import messages
            messages.error(request, "Keep at least one tab visible.")
        else:
            pref.hidden = action == "hide"
            pref.save(update_fields=("hidden",))
    elif action in {"up", "down"} and pref:
        index = prefs.index(pref)
        other = index + (-1 if action == "up" else 1)
        if 0 <= other < len(prefs):
            prefs[index], prefs[other] = prefs[other], prefs[index]
            for index, item in enumerate(prefs):
                item.position = index
                item.save(update_fields=("position",))
    return redirect(url)


def apply_work_filters(runs, params):
    pending = RunSubmission.objects.filter(run_id=OuterRef("pk"), status="received").exclude(run__lifecycle_status__in=("invalidated",))
    evidence = RunSubmission.objects.filter(run_id=OuterRef("pk"), status="awaiting_evidence").exclude(run__lifecycle_status__in=("invalidated",))
    latest_audit = SubmissionAuditEntry.objects.filter(submission_id=OuterRef("pk")).order_by("-created_at", "-pk")
    accepted = RunSubmission.objects.filter(status="approved").annotate(audit_state=Subquery(latest_audit.values("outcome")[:1]))
    runs = runs.annotate(needs_review=Exists(pending), needs_evidence=Exists(evidence))
    if params.get("work") == "review":
        runs = runs.filter(needs_review=True)
    elif params.get("work") == "evidence":
        runs = runs.filter(needs_evidence=True)
    audit = params.get("audit")
    if audit == "unaudited":
        accepted = accepted.filter(Q(audit_state__isnull=True) | ~Q(audit_state="passed"))
    elif audit:
        accepted = accepted.filter(audit_state=audit)
    vod = params.get("vod")
    if vod:
        now = timezone.now()
        matching = []
        for sub in accepted.filter(Q(audit_state__isnull=True) | ~Q(audit_state="passed")).only("run_id", "evidence_check"):
            try:
                published = parse_datetime(sub.evidence_check.get("published_at") or "")
            except (ValueError, TypeError):
                published = None
            if published and timezone.is_naive(published):
                published = timezone.make_aware(published)
            deadline = published + timedelta(days=7) if published else None
            if ((vod == "unknown" and deadline is None) or
                (vod == "closing" and deadline and now < deadline <= now + timedelta(hours=48)) or
                (vod == "expired" and deadline and deadline <= now)):
                matching.append(sub.run_id)
        runs = runs.filter(pk__in=matching)
    elif audit:
        runs = runs.filter(pk__in=accepted.values("run_id"))
    return runs
