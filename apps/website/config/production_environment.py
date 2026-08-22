from cryptography.fernet import Fernet
from urllib.parse import urlparse


TURNSTILE_TEST_SITE_KEY = "1x00000000000000000000AA"
TURNSTILE_TEST_SECRET_KEY = "1x0000000000000000000000000000000AA"

REQUIRED_PRODUCTION_VARIABLES = (
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "SITE_PUBLIC_URL",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "MICROSOFT_GRAPH_TENANT_ID",
    "MICROSOFT_GRAPH_CLIENT_ID",
    "MICROSOFT_GRAPH_CLIENT_SECRET",
    "MICROSOFT_GRAPH_SENDER",
    "MICROSOFT_GRAPH_REPLY_TO",
    "DEFAULT_FROM_EMAIL",
    "TURNSTILE_SITE_KEY",
    "TURNSTILE_SECRET_KEY",
    "OPENAI_API_KEY",
    "STREAMING_TOKEN_ENCRYPTION_KEY",
    "TWITCH_CLIENT_ID",
    "TWITCH_CLIENT_SECRET",
    "TWITCH_REDIRECT_URI",
    "DISCORD_CLIENT_ID",
    "DISCORD_CLIENT_SECRET",
    "DISCORD_REDIRECT_URI",
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REDIRECT_URI",
    "STEAMCMD_EXECUTABLE",
    "STEAMCMD_USERNAME",
    "STEAM_WEB_API_KEY",
    "PZ_REFERENCE_ROOT",
    "JAVA_EXECUTABLE",
    "VINEFLOWER_JAR",
    "PZ_DECOMPILED_ROOT",
    "STATIC_ROOT",
    "MEDIA_ROOT",
    "AVATAR_QUARANTINE_ROOT",
    "RELEASE_ID",
)


def parse_boolean(value, *, name):
    normalised = str(value).strip().lower()
    if normalised in {"1", "true", "yes", "on"}:
        return True
    if normalised in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be true or false.")


def parse_positive_integer(value, *, name, allow_zero=False):
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    minimum = 0 if allow_zero else 1
    if parsed < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}.")
    return parsed


def split_list(value):
    return [item.strip() for item in str(value).split(",") if item.strip()]


def validate_production_environment(environ):
    runtime_state_backend = environ.get("RUNTIME_STATE_BACKEND", "cache").strip().lower()
    if runtime_state_backend not in {"cache", "database"}:
        raise RuntimeError("RUNTIME_STATE_BACKEND must be cache or database.")
    missing = [
        name for name in REQUIRED_PRODUCTION_VARIABLES if not environ.get(name, "").strip()
    ]
    if runtime_state_backend == "cache" and not environ.get("REDIS_URL", "").strip():
        missing.append("REDIS_URL")
    if missing:
        raise RuntimeError(
            "Production configuration is incomplete. Missing: "
            + ", ".join(sorted(missing))
        )

    staging_environment = parse_boolean(
        environ.get("STAGING_ENVIRONMENT", "false"),
        name="STAGING_ENVIRONMENT",
    )
    if not staging_environment and environ["TURNSTILE_SITE_KEY"] == TURNSTILE_TEST_SITE_KEY:
        raise RuntimeError("TURNSTILE_SITE_KEY must not use the localhost test key.")
    if not staging_environment and environ["TURNSTILE_SECRET_KEY"] == TURNSTILE_TEST_SECRET_KEY:
        raise RuntimeError("TURNSTILE_SECRET_KEY must not use the localhost test key.")

    public_url = environ["SITE_PUBLIC_URL"].strip()
    if not public_url.startswith("https://"):
        raise RuntimeError("SITE_PUBLIC_URL must use HTTPS in production.")
    public_host = urlparse(public_url).hostname

    for name in (
        "TWITCH_REDIRECT_URI",
        "DISCORD_REDIRECT_URI",
        "YOUTUBE_REDIRECT_URI",
    ):
        if not environ[name].strip().startswith("https://"):
            raise RuntimeError(f"{name} must use HTTPS in production.")

    try:
        Fernet(environ["STREAMING_TOKEN_ENCRYPTION_KEY"].encode("ascii"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "STREAMING_TOKEN_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc

    split_values = {
        "allowed_hosts": split_list(environ["DJANGO_ALLOWED_HOSTS"]),
        "csrf_trusted_origins": split_list(
            environ["DJANGO_CSRF_TRUSTED_ORIGINS"]
        ),
    }
    if not split_values["allowed_hosts"]:
        raise RuntimeError("DJANGO_ALLOWED_HOSTS must contain at least one host.")
    if public_host not in split_values["allowed_hosts"]:
        raise RuntimeError(
            "DJANGO_ALLOWED_HOSTS must include the SITE_PUBLIC_URL host."
        )
    if not split_values["csrf_trusted_origins"] or any(
        not origin.startswith("https://")
        for origin in split_values["csrf_trusted_origins"]
    ):
        raise RuntimeError(
            "DJANGO_CSRF_TRUSTED_ORIGINS must contain HTTPS origins only."
        )
    if public_url.rstrip("/") not in {
        origin.rstrip("/") for origin in split_values["csrf_trusted_origins"]
    }:
        raise RuntimeError(
            "DJANGO_CSRF_TRUSTED_ORIGINS must include SITE_PUBLIC_URL."
        )

    secret_key = environ["DJANGO_SECRET_KEY"]
    if len(secret_key) < 50 or secret_key.startswith("django-insecure-"):
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be a strong production-only value."
        )

    integer_values = {
        "postgres_port": parse_positive_integer(
            environ["POSTGRES_PORT"], name="POSTGRES_PORT"
        ),
        "postgres_conn_max_age": parse_positive_integer(
            environ.get("POSTGRES_CONN_MAX_AGE", "0"),
            name="POSTGRES_CONN_MAX_AGE",
            allow_zero=True,
        ),
        "secure_hsts_seconds": parse_positive_integer(
            environ.get("DJANGO_SECURE_HSTS_SECONDS", "3600"),
            name="DJANGO_SECURE_HSTS_SECONDS",
            allow_zero=True,
        ),
    }

    if integer_values["postgres_conn_max_age"] != 0:
        raise RuntimeError(
            "POSTGRES_CONN_MAX_AGE must be 0 because production runs under ASGI."
        )

    return {
        **split_values,
        **integer_values,
        "runtime_state_backend": runtime_state_backend,
        "trust_cloudflare_connecting_ip": parse_boolean(
            environ.get("TRUST_CLOUDFLARE_CONNECTING_IP", "true"),
            name="TRUST_CLOUDFLARE_CONNECTING_IP",
        ),
    }
