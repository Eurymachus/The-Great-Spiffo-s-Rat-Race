import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import ReferenceSource, ReferenceUpdateJob
from .reference_paths import resolved_reference_paths
from .reference_update import installed_build_id, notify_superusers


SENTINEL = Path("zombie/characters/skills/PerkFactory.java")


def _finish(job, source, status, summary, build_id=""):
    now = timezone.now()
    job.status = status
    job.installed_build_id = build_id
    job.finished_at = now
    job.summary = summary
    job.save(update_fields=("status", "installed_build_id", "finished_at", "summary"))
    source.last_checked_at = now
    source.last_error = (
        summary if status == ReferenceUpdateJob.Status.FAILED else ""
    )
    if status == ReferenceUpdateJob.Status.UPDATED:
        source.decompiled_build_id = build_id
        source.decompiled_at = now
    source.save()
    return job


def run_decompilation(job):
    source = job.source
    paths = resolved_reference_paths()
    install_root = paths.install_root
    input_jar = install_root / "projectzomboid.jar"
    output_parent = paths.decompiled_parent
    decompiler = paths.vineflower_jar
    java_value = paths.java_executable
    java = shutil.which(java_value) or (
        str(Path(java_value)) if Path(java_value).is_file() else ""
    )
    build_id = installed_build_id(install_root)
    job.previous_build_id = source.decompiled_build_id
    job.save(update_fields=("previous_build_id",))

    if not build_id:
        return _finish(
            job, source, ReferenceUpdateJob.Status.FAILED,
            "The installed Project Zomboid build ID could not be read."
        )
    if not input_jar.is_file() or not decompiler.is_file() or not java:
        return _finish(
            job,
            source,
            ReferenceUpdateJob.Status.FAILED,
            "Configure valid Java, Vineflower and Project Zomboid paths in the "
            "protected deployment environment first.",
            build_id,
        )

    output_parent.mkdir(parents=True, exist_ok=True)
    output_root = output_parent / f"build-{build_id}-job-{job.pk}"
    staging = Path(
        tempfile.mkdtemp(prefix=".staging-", dir=output_parent)
    )
    try:
        completed = subprocess.run(
            [
                java,
                "-jar",
                str(decompiler),
                "--folder",
                "--log-level=WARN",
                str(input_jar),
                str(staging),
            ],
            capture_output=True,
            text=True,
            timeout=getattr(settings, "PZ_DECOMPILATION_TIMEOUT_SECONDS", 3600),
            check=False,
        )
        if completed.returncode:
            return _finish(
                job,
                source,
                ReferenceUpdateJob.Status.FAILED,
                f"Vineflower exited with code {completed.returncode}.",
                build_id,
            )
        if not (staging / SENTINEL).is_file():
            return _finish(
                job,
                source,
                ReferenceUpdateJob.Status.FAILED,
                f"Decompiled output failed validation: {SENTINEL} is missing.",
                build_id,
            )
        marker = staging / ".tgsrr-build-id"
        marker.write_text(f"{build_id}\n", encoding="utf-8")
        if output_root.exists():
            shutil.rmtree(output_root)
        staging.rename(output_root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _finish(
            job,
            source,
            ReferenceUpdateJob.Status.FAILED,
            f"Decompilation could not complete: {type(exc).__name__}.",
            build_id,
        )
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    summary = f"Project Zomboid build {build_id} was decompiled and validated."
    notify_superusers("Project Zomboid reference decompiled", summary)
    return _finish(
        job, source, ReferenceUpdateJob.Status.UPDATED, summary, build_id
    )
