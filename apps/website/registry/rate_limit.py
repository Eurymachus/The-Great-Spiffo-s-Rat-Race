import hashlib

from django.core.cache import cache


def request_ip(request):
    from django.conf import settings

    if settings.TRUST_CLOUDFLARE_CONNECTING_IP:
        cloudflare_ip = request.headers.get("CF-Connecting-IP")
        if cloudflare_ip:
            return cloudflare_ip.strip()
    return request.META.get("REMOTE_ADDR", "unknown").strip()


def exceeded(scope, identifier, limit, window_seconds):
    digest = hashlib.sha256(identifier.casefold().encode("utf-8")).hexdigest()
    key = f"rat-race-rate:{scope}:{digest}"
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        attempts = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return attempts > limit
