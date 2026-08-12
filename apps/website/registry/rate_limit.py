from operations.runtime_state import rate_limit_exceeded


def request_ip(request):
    from django.conf import settings

    if settings.TRUST_CLOUDFLARE_CONNECTING_IP:
        cloudflare_ip = request.headers.get("CF-Connecting-IP")
        if cloudflare_ip:
            return cloudflare_ip.strip()
    return request.META.get("REMOTE_ADDR", "unknown").strip()


def exceeded(scope, identifier, limit, window_seconds):
    return rate_limit_exceeded(scope, identifier, limit, window_seconds)
