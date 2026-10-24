"""Personal and shared filters for the Rat Race 1.0 workspace."""
from django.db import transaction
from django.db.models import Q
from django.http import QueryDict, Http404
from django.shortcuts import redirect
from django.urls import reverse
from .models import LegacySavedView, LegacyViewPreference, LegacyWorkspacePreference

WORKSPACES = {
    "runs": "legacyrun", "updates": "legacyrunsubmission",
    "claims": "legacyrunclaim", "imports": "legacydataimport",
}
FILTERS = ("workspace", "q", "o", "lifecycle__exact", "status__exact", "source__exact")
DEFAULT_TAB_ORDER = ("claims", "updates", "all", "active", "imports")


def permitted(user, workspace):
    model = WORKSPACES.get(workspace)
    if not model:
        return False
    if workspace == "imports":
        return user.is_active and user.is_superuser
    return user.has_perm(f"registry.view_{model}") or user.has_perm(f"registry.change_{model}")



def clean_filters(data):
    kind = data.get("workspace", "runs")
    if kind not in WORKSPACES:
        raise Http404
    result = {key: str(data.get(key, ""))[:200] for key in FILTERS}
    result["workspace"] = kind
    if kind == "runs":
        result["status__exact"] = result["source__exact"] = ""
    else:
        result["lifecycle__exact"] = ""
        if kind != "updates":
            result["source__exact"] = ""
    return result


def available(user):
    return LegacySavedView.objects.filter(Q(shared=True) | Q(owner=user), filters__workspace__in=[kind for kind in WORKSPACES if permitted(user, kind)])


def preferences(user):
    existing = set(LegacyViewPreference.objects.filter(user=user).values_list("view_id", flat=True))
    position = max(LegacyViewPreference.objects.filter(user=user).values_list("position", flat=True), default=-1) + 1
    views = sorted(available(user), key=lambda view: (
        DEFAULT_TAB_ORDER.index(view.system_key) if view.system_key in DEFAULT_TAB_ORDER else len(DEFAULT_TAB_ORDER), view.pk
    ))
    for view in views:
        if view.pk not in existing:
            LegacyViewPreference.objects.get_or_create(user=user, view=view, defaults={"position": position})
            position += 1
    return list(LegacyViewPreference.objects.filter(user=user, view__in=available(user)).select_related("view").order_by("position", "pk"))


def resolve_view(request):
    prefs = preferences(request.user)
    visible = [p for p in prefs if not p.hidden]
    if not visible and prefs:
        prefs[0].hidden = False
        prefs[0].save(update_fields=("hidden",))
        visible = [prefs[0]]
    workspace, _ = LegacyWorkspacePreference.objects.get_or_create(user=request.user)
    selected = next((p for p in visible if str(p.view_id) == request.GET.get("view")), None)
    if not selected and "view" not in request.GET:
        selected = next((p for p in visible if p.view_id == workspace.last_view_id), None)
    selected = selected or (visible[0] if visible else None)
    if "workspace" in request.GET and "view" not in request.GET:
        selected = next((p for p in visible if p.view.filters.get("workspace") == request.GET["workspace"]), None)
    if selected and "workspace" in request.GET and request.GET["workspace"] != selected.view.filters.get("workspace"):
        raise Http404
    if "view" in request.GET and not any(str(p.view_id) == request.GET["view"] for p in visible):
        raise Http404
    params = QueryDict(mutable=True)
    if selected:
        params.update(clean_filters(selected.filters or selected.view.filters))
        if "reset" in request.GET:
            params = QueryDict(mutable=True)
            params.update(clean_filters(selected.view.filters))
    if "_filters" in request.GET:
        params = QueryDict(mutable=True)
        params["workspace"] = selected.view.filters["workspace"] if selected else request.GET.get("workspace", "runs")
    for key in FILTERS:
        if key in request.GET:
            params[key] = request.GET[key]
    for key, value in clean_filters(params).items():
        params[key] = value
    if not permitted(request.user, params.get("workspace", "runs")):
        raise Http404
    if selected:
        params["view"] = str(selected.view_id)
        selected.filters = clean_filters(params)
        selected.save(update_fields=("filters",))
        workspace.last_view = selected.view
        workspace.save(update_fields=("last_view",))
    if "claim" in request.GET:
        params["claim"] = request.GET["claim"]
    if "p" in request.GET:
        params["p"] = request.GET["p"]
    return params, {
        "saved_tabs": visible, "managed_tabs": prefs, "selected_view": selected.view if selected else None,
        "can_edit_view": bool(selected and (request.user.has_perm("registry.manage_shared_legacy_views") if selected.view.shared else selected.view.owner_id == request.user.pk)),
        "can_share_views": request.user.has_perm("registry.manage_shared_legacy_views"),
        "saved_filter_fields": list(clean_filters(params).items()),
    }


@transaction.atomic
def manage_view(request):
    if not any(permitted(request.user, kind) for kind in WORKSPACES):
        raise Http404
    action = request.POST.get("action")
    view_id = request.POST.get("view", "")
    view = available(request.user).filter(pk=view_id if view_id.isdigit() else None).first()
    can_share = request.user.has_perm("registry.manage_shared_legacy_views")
    can_edit = view and (can_share if view.shared else view.owner_id == request.user.pk)
    url = reverse("admin:registry_legacyrun_changelist")
    prefs = preferences(request.user)
    pref = next((p for p in prefs if view and p.view_id == view.pk), None)
    if action == "reorder":
        from django.http import JsonResponse
        order = request.POST.getlist("order")
        visible = {str(p.view_id): p for p in prefs if not p.hidden}
        if len(order) != len(visible) or set(order) != set(visible):
            return JsonResponse({"error": "The tabs changed. Refresh and try again."}, status=400)
        ordered = [visible[key] for key in order] + [p for p in prefs if p.hidden]
        for position, item in enumerate(ordered):
            item.position = position
            item.save(update_fields=("position",))
        return JsonResponse({"saved": True})

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
            view = LegacySavedView(owner=request.user)
        filters = clean_filters(request.POST)
        if not permitted(request.user, filters["workspace"]):
            raise Http404
        view.name, view.shared, view.filters = name, shared, filters
        view.save()
        # A shared edit takes effect for everyone, including their remembered overrides.
        LegacyViewPreference.objects.filter(view=view).update(filters={})
        LegacyViewPreference.objects.get_or_create(user=request.user, view=view, defaults={"position": len(prefs)})
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

