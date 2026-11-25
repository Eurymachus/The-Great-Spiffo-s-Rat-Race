from django.conf import settings
from django.http.request import split_domain_port
from django.template.response import TemplateResponse
from .release_controls import MESSAGES, enabled, model_available, route_control


class ReleaseControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        control = route_control(match, request.method)
        model_admin = getattr(view_func, "model_admin", None)
        if model_admin and not model_available(model_admin.model._meta.label_lower):
            control = "rr2"
        # Autocomplete uses one generic admin URL for every model.
        if match.view_name == "admin:autocomplete":
            label = f"{request.GET.get('app_label', '')}.{request.GET.get('model_name', '')}"
            if not model_available(label):
                control = "rr2"
        if control and not enabled(control):
            response = TemplateResponse(request, "release_closed.html", {
                "release_message": MESSAGES[control],
            }, status=403)
            response["Cache-Control"] = "no-store"
            return response
        return None


class MaintenanceModeMiddleware:
    """Hold public traffic while leaving local access and health checks available."""

    health_paths = frozenset({"/health/live/", "/health/ready/"})
    local_hosts = frozenset({"localhost", "127.0.0.1", "[::1]"})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host, _ = split_domain_port(request.get_host().lower())
        if (
            not settings.SITE_MAINTENANCE_MODE
            or request.path in self.health_paths
            or host in self.local_hosts
        ):
            return self.get_response(request)

        response = TemplateResponse(
            None,
            "maintenance.html",
            status=503,
        )
        response["Retry-After"] = "3600"
        response["Cache-Control"] = "no-store, max-age=0"
        return response.render()


class DevelopmentNoStoreMiddleware:
    """Prevent browser caching from obscuring local frontend changes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG:
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
