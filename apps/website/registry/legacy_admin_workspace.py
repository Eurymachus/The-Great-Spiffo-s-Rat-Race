"""One saved-view workspace for Rat Race 1.0 administration."""
from django.apps import apps
from django.http import Http404
from django.contrib.admin.utils import quote
from django.urls import reverse
from .legacy_saved_views import WORKSPACES, manage_view, resolve_view


class LegacyWorkspaceMixin:
    change_list_template = "admin/registry/legacy_workspace.html"
    actions = None

    def changelist_view(self, request, extra_context=None):
        context = dict(extra_context or {})
        if not getattr(request, "legacy_workspace_resolved", False):
            if request.method == "POST" and request.POST.get("saved_view_action"):
                request.POST = request.POST.copy()
                request.POST["action"] = request.POST["saved_view_action"]
                return manage_view(request)
            # Old list links retain their dataset and explicit filters.
            if self.model._meta.model_name != "legacyrun" and "view" not in request.GET:
                request.GET = request.GET.copy()
                kind = next(key for key, value in WORKSPACES.items() if value == self.model._meta.model_name)
                request.GET["workspace"] = kind
            params, saved_context = resolve_view(request)
            request.GET = params
            request.legacy_workspace_resolved = True
            context.update(saved_context)
            target = self.admin_site._registry[apps.get_model("registry", WORKSPACES[params["workspace"]])]
            if not target.has_view_or_change_permission(request):
                raise Http404
            if target is not self:
                return target.changelist_view(request, extra_context=context)
        context["title"] = "Rat Race 1.0"
        response = super().changelist_view(request, extra_context=context)
        if hasattr(response, "context_data") and response.context_data and "cl" in response.context_data:
            # Keep the selected tab in search, pagination and ordering URLs.
            response.context_data["cl"].params["view"] = request.GET.get("view", "")
            response.context_data["cl"].filter_params["view"] = [request.GET.get("view", "")]
            # Rows belong to the selected dataset, even though every tab shares a URL.
            opts = self.model._meta
            response.context_data["cl"].url_for_result = lambda result: reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change", args=(quote(result.pk),)
            )
        return response

    def get_changelist_instance(self, request):
        original = request.GET
        request.GET = original.copy()
        for key in ("view", "workspace", "reset", "_filters"):
            request.GET.pop(key, None)
        for key in list(request.GET):
            if not request.GET[key]:
                request.GET.pop(key)
        try:
            return super().get_changelist_instance(request)
        finally:
            request.GET = original
