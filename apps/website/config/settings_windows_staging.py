import os

os.environ["STAGING_ENVIRONMENT"] = "true"

from .settings_windows_production import *  # noqa: F403


EMAIL_BACKEND = "config.staging_email.AllowlistedStagingEmailBackend"
STAGING_ENVIRONMENT = True
MIDDLEWARE.insert(0, "config.staging.StagingNoIndexMiddleware")  # noqa: F405
STAGING_EMAIL_ALLOW_ALL = os.environ.get(
    "STAGING_EMAIL_ALLOW_ALL", "false"
).strip().lower() in {"1", "true", "yes", "on"}
STAGING_EMAIL_ALLOWLIST = {
    address.strip().lower()
    for address in os.environ.get("STAGING_EMAIL_ALLOWLIST", "").split(",")
    if address.strip()
}
