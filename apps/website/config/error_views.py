from django.contrib import admin
from django.shortcuts import render
from django.urls import reverse
from django.views.defaults import permission_denied as default_permission_denied


def permission_denied(request, exception):
    if request.path.startswith(reverse("admin:index")) and admin.site.has_permission(request):
        match = request.resolver_match
        model_admin = getattr(getattr(match, "func", None), "model_admin", None)
        destination = "this page"
        if model_admin and match.url_name.endswith("_changelist"):
            destination = str(model_admin.model._meta.verbose_name_plural)
        response = render(request, "admin/permission_denied.html", {
            **admin.site.each_context(request),
            "title": "Permission denied",
            "permission_message": f"You don't have permission to view {destination}.",
        }, status=403)
        response["Cache-Control"] = "no-store"
        return response
    return default_permission_denied(request, exception)
