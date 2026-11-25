"""Environment-owned release policy shared by HTTP, presentation and workers."""
from urllib.parse import urlsplit

from django.conf import settings
from django.urls import Resolver404, resolve


CONTROLS = {
    "registration": "REGISTRATION_ENABLED",
    "workshop_submissions": "WORKSHOP_SUBMISSIONS_ENABLED",
    "rr1_submissions": "RR1_SUBMISSIONS_ENABLED",
    "rr2": "RR2_ENABLED",
}
MESSAGES = {
    "registration": "New account registration is currently closed. Existing accounts can still sign in.",
    "workshop_submissions": "New Workshop mod requests are currently closed. Published rulings remain available.",
    "rr1_submissions": "Rat Race 1.0 claims and updates are currently closed. Existing results remain available.",
    "rr2": "Rat Race 2.0 is in development and is not open yet.",
}
RR2_MODELS = frozenset({
    "registry.challengemode", "registry.challengemodealias",
    "registry.participantchallengemodelimit", "registry.challengerun",
    "registry.runsubmission", "registry.submissionaudit",
    "operations.dailyleaderboardschedule", "operations.dailyleaderboardjob",
    "operations.rundatadangerzone",
})
ROUTE_CONTROLS = {
    "registry:register": "registration",
    "registry:validate_registration_field": "registration",
    "registry:workshop_mod_lookup": "workshop_submissions",
    "registry:claim_legacy_run": "rr1_submissions",
    "registry:submit_legacy_run": "rr1_submissions",
    "registry:submit_run": "rr2",
    "registry:update_run_submission_evidence": "rr2",
    "registry:deactivate_run": "rr2",
    "registry:public_run_detail": "rr2",
    "registry:leaderboard": "rr2",
    "registry:exploits": "rr2",
}


def parse_release_control(value, *, name):
    value = str(value).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false.")


def enabled(control):
    # Exact booleans prevent a string such as "false" from opening a feature.
    return getattr(settings, CONTROLS[control], False) is True


def release_state():
    return {control: enabled(control) for control in CONTROLS}


def model_available(label):
    return enabled("rr2") or label.lower() not in RR2_MODELS


def route_control(match, method="GET"):
    if match.view_name == "registry:mods" and method not in {"GET", "HEAD", "OPTIONS"}:
        return "workshop_submissions"
    if match.namespace == "admin":
        for label in RR2_MODELS:
            if (match.url_name or "").startswith(label.replace(".", "_") + "_"):
                return "rr2"
    return ROUTE_CONTROLS.get(match.view_name)


def destination_available(destination):
    """Filter known internal feature links without editing managed content."""
    parts = urlsplit(destination or "")
    if parts.netloc and parts.netloc != urlsplit(settings.SITE_PUBLIC_URL).netloc:
        return True
    if not parts.path.startswith("/"):
        return True
    try:
        match = resolve(parts.path)
    except Resolver404:
        return True
    control = route_control(match)
    if control:
        return enabled(control)
    if not enabled("rr2") and (
        match.view_name == "registry:page" or match.func.__name__ == "media_page"
    ):
        from pages.models import Page

        return not Page.objects.filter(public_path=parts.path.strip("/"), required_release="rr2").exists()
    return True
