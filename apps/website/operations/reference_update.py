import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from registry.models import Notification, Participant

from .models import ReferenceSource, ReferenceUpdateJob


BUILD_ID = re.compile(r'"buildid"\s+"(?P<build_id>\d+)"')
AUTH_FAILURE_MARKERS = (
    "account logon denied",
    "account login denied",
    "invalid password",
    "steam guard",
    "two-factor code",
)


def installed_build_id(library_root):
    root = Path(library_root)
    candidates = (
        root / "steamapps" / "appmanifest_108600.acf",
        root.parent.parent / "appmanifest_108600.acf",
    )
    for manifest in candidates:
        if manifest.exists():
            match = BUILD_ID.search(
                manifest.read_text(encoding="utf-8", errors="replace")
            )
            if match:
                return match.group("build_id")
    return ""


def notify_superusers(title, message):
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                category=Notification.Category.EVENT,
                title=title,
                message=message[:300],
                destination="/admin/operations/referencesource/",
            )
            for user in Participant.objects.filter(is_superuser=True, is_active=True)
        ]
    )


def _finish_failure(job, source, summary):
    now = timezone.now()
    job.status = ReferenceUpdateJob.Status.FAILED
    job.finished_at = now
    job.summary = summary
    job.save(update_fields=("status", "finished_at", "summary"))
    source.authentication_status = ReferenceSource.AuthenticationStatus.ERROR
    source.last_checked_at = now
    source.last_error = summary
    source.save(
        update_fields=("authentication_status", "last_checked_at", "last_error")
    )
    notify_superusers("Project Zomboid reference update failed", summary)


def run_reference_update(job):
    source = job.source
    executable_value = source.steamcmd_path or settings.STEAMCMD_EXECUTABLE
    install_root_value = source.install_root or settings.PZ_REFERENCE_ROOT
    username = (source.account_name or settings.STEAMCMD_USERNAME).strip()
    executable = Path(executable_value) if executable_value else Path()
    install_root = Path(install_root_value) if install_root_value else Path()
    if (
        not username
        or not install_root_value
        or not executable_value
        or not executable.is_file()
    ):
        summary = (
            "Connect Steam and configure valid SteamCMD and installation paths "
            "on the Project Zomboid reference source first."
        )
        _finish_failure(job, source, summary)
        return job

    previous = installed_build_id(install_root)
    job.previous_build_id = previous
    job.save(update_fields=("previous_build_id",))
    try:
        completed = subprocess.run(
            [
                str(executable),
                "+force_install_dir",
                str(install_root),
                "+login",
                username,
                "+app_update",
                "108600",
                "validate",
                "+quit",
            ],
            capture_output=True,
            text=True,
            timeout=settings.STEAMCMD_UPDATE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _finish_failure(
            job, source, f"SteamCMD could not complete: {type(exc).__name__}."
        )
        return job

    output = "\n".join((completed.stdout, completed.stderr)).strip()
    now = timezone.now()
    current = installed_build_id(install_root)
    auth_failed = any(marker in output.casefold() for marker in AUTH_FAILURE_MARKERS)
    if auth_failed:
        status = ReferenceUpdateJob.Status.AUTHENTICATION_REQUIRED
        auth_status = ReferenceSource.AuthenticationStatus.AUTHENTICATION_REQUIRED
        summary = "Steam authentication is required on the host."
        notify_superusers("Steam authentication required", summary)
    elif completed.returncode:
        status = ReferenceUpdateJob.Status.FAILED
        auth_status = ReferenceSource.AuthenticationStatus.ERROR
        summary = f"SteamCMD exited with code {completed.returncode}."
        notify_superusers("Project Zomboid reference update failed", summary)
    else:
        status = (
            ReferenceUpdateJob.Status.UPDATED
            if current and current != previous
            else ReferenceUpdateJob.Status.UNCHANGED
        )
        auth_status = ReferenceSource.AuthenticationStatus.AUTHENTICATED
        summary = (
            f"Installed Project Zomboid build changed from "
            f"{previous or 'none'} to {current}."
            if status == ReferenceUpdateJob.Status.UPDATED
            else f"Project Zomboid build {current or 'unknown'} is current."
        )
        if status == ReferenceUpdateJob.Status.UPDATED:
            notify_superusers("Project Zomboid reference updated", summary)

    job.status = status
    job.installed_build_id = current
    job.finished_at = now
    job.summary = summary
    job.save(update_fields=("status", "installed_build_id", "finished_at", "summary"))
    source.authentication_status = auth_status
    source.installed_build_id = current
    source.last_checked_at = now
    source.last_error = (
        summary
        if status
        in {
            ReferenceUpdateJob.Status.FAILED,
            ReferenceUpdateJob.Status.AUTHENTICATION_REQUIRED,
        }
        else ""
    )
    if status == ReferenceUpdateJob.Status.UPDATED:
        source.last_updated_at = now
    source.save()
    return job
