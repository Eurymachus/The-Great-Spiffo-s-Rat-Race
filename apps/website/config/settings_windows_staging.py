import os

os.environ["STAGING_ENVIRONMENT"] = "true"

from .settings_windows_production import *  # noqa: F403


EMAIL_BACKEND = "config.staging_email.AllowlistedStagingEmailBackend"
STAGING_ENVIRONMENT = True
STAGING_EMAIL_ALLOWLIST = {
    address.strip().lower()
    for address in os.environ["STAGING_EMAIL_ALLOWLIST"].split(",")
    if address.strip()
}
