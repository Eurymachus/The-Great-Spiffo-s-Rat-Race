from urllib.parse import urlsplit


def is_safe_managed_destination(value):
    destination = str(value or "").strip()
    if destination.startswith("/") and not destination.startswith("//"):
        return True
    if destination.startswith("#"):
        return True
    return urlsplit(destination).scheme.lower() == "https"
