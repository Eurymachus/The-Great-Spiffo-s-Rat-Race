from django.conf import settings
from django.http.request import split_domain_port
from django.template.response import TemplateResponse


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
