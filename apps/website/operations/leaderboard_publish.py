"""Unlisted DEV leaderboard packaging and audited Workshop publication."""
import hashlib
import json
import math
import logging
import re
import shutil
import subprocess
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from registry.leaderboard import build_current_leaderboard
from .models import DailyLeaderboardJob as Job, DailyLeaderboardSchedule as Schedule
from .reference_update import notify_superusers
from .steam_lock import SteamBusy, steam_lock

TEST_ITEM_ID = "3842654789"
TEMPLATE = Path(__file__).resolve().parents[3] / "deployment" / "leaderboard-mod"
ACTIVE = (Job.Status.QUEUED, Job.Status.RUNNING, Job.Status.UNCERTAIN)
logger = logging.getLogger(__name__)


def configuration():
    if not settings.LEADERBOARD_PUBLISH_ENABLED or not getattr(settings, "STAGING_ENVIRONMENT", False):
        raise ValueError("Leaderboard publication is enabled only on the DEV service.")
    if settings.LEADERBOARD_WORKSHOP_ID != TEST_ITEM_ID:
        raise ValueError("The publisher must target the existing Unlisted test item.")
    username = settings.LEADERBOARD_STEAM_USERNAME
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", username):
        raise ValueError("Configure the Workshop owner's Steam account.")
    executable = Path(settings.STEAMCMD_EXECUTABLE)
    root = Path(settings.LEADERBOARD_PACKAGE_ROOT)
    if not executable.is_absolute() or not executable.is_file() or not root.is_absolute():
        raise ValueError("Configure absolute publisher storage and a valid SteamCMD executable.")
    return executable, username, root


@transaction.atomic
def enqueue(*, scheduled=False, now=None):
    configuration()
    schedule, _ = Schedule.objects.get_or_create(pk=1)
    schedule = Schedule.objects.select_for_update().get(pk=1)
    schedule.full_clean()
    day = None
    if scheduled:
        if not schedule.enabled:
            return None
        local = (now or timezone.now()).astimezone(ZoneInfo(schedule.timezone_name))
        if local.time().replace(tzinfo=None) < time(schedule.hour, schedule.minute):
            return None
        day = local.date()
        existing = Job.objects.filter(schedule=schedule, scheduled_day=day).first()
        if existing:
            return existing
    active = Job.objects.filter(schedule=schedule, status__in=ACTIVE).first()
    if active:
        return active
    return Job.objects.create(schedule=schedule, scheduled_day=day)


def tick():
    if not settings.LEADERBOARD_PUBLISH_ENABLED:
        return
    # An invalid deployment configuration must never take down the worker.
    # The admin/management command reports configuration errors explicitly.
    if not getattr(settings, "STAGING_ENVIRONMENT", False):
        return
    try:
        executable, _, _ = configuration()
        enqueue(scheduled=True)
    except (ValueError, ValidationError):
        logger.error("Daily leaderboard configuration is invalid; publication remains disabled.")
        return
    try:
        with steam_lock(executable):
            _publish_queued_job()
    except SteamBusy:
        return
    except OSError:
        logger.error("Daily leaderboard could not open the SteamCMD lock.")


def _publish_queued_job():
    with transaction.atomic():
        schedule = Schedule.objects.select_for_update().get(pk=1)
        if Job.objects.filter(schedule=schedule, status__in=(Job.Status.RUNNING, Job.Status.UNCERTAIN)).exists():
            return
        job = Job.objects.filter(schedule=schedule, status=Job.Status.QUEUED).order_by("pk").first()
        if not job:
            return
        job.status = Job.Status.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=("status", "started_at"))
    publish(job)


def lua(value):
    """Serialize data, never interpolate participant text as Lua source."""
    if value is None:
        return "nil"
    if isinstance(value, str):
        escaped = ''.join(
            '\\' + c if c in ('\\', '"') else f"\\{ord(c):03d}" if ord(c) < 32 or ord(c) == 127 else c
            for c in value
        )
        return '"' + escaped + '"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and math.isfinite(value):
        return str(value)
    if isinstance(value, list):
        return "{" + ",".join(lua(item) for item in value) + "}"
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua(key) + "]=" + lua(item) for key, item in value.items()) + "}"
    raise ValueError("Unsupported snapshot value.")


def snapshot():
    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        rows = build_current_leaderboard()
        return [{
            "rank": row["rank"], "racer": row["racer"], "survivor": row["survivor"],
            "completion": row["completion"], "kills": row["kills"],
            "outposts": row["outposts_completed"], "skills": row["maxed_skills"],
            "day": row["in_game_day"],
        } for row in rows]


def data_hash(rows):
    if not (TEMPLATE / "mods/TGSRRDailyLeaderboardProbe/42/mod.info").is_file():
        raise ValueError("Leaderboard mod template is missing.")
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    digest.update(b"leaderboard-schema-1")
    for file in sorted(TEMPLATE.rglob("*")):
        if file.is_file():
            digest.update(file.relative_to(TEMPLATE).as_posix().encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()


def package(job, rows, root):
    target = root / f"job-{job.pk}"
    target.mkdir(parents=True, exist_ok=False)
    shutil.copytree(TEMPLATE, target / "Contents")
    (target / "Contents/mods/TGSRRDailyLeaderboardProbe/common").mkdir()
    payload = {"schema": 1, "source": "Hosted DEV - test standings", "asOfUtc": timezone.now().isoformat(), "rows": rows}
    data = target / "Contents/mods/TGSRRDailyLeaderboardProbe/42/media/lua/client/TGSRRDailyLeaderboardData.lua"
    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text("TGSRRDailyLeaderboardData = " + lua(payload) + "\n", encoding="utf-8")
    (target / "snapshot.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = {"appid": "108600", "publishedfileid": TEST_ITEM_ID,
              "contentfolder": (target / "Contents").as_posix(), "visibility": "3",
              "description": "Unlisted hosted DEV test for TGSRR Daily Leaderboard. Contains test-environment standings. Not affiliated with The Indie Stone.",
              "changenote": f"Hosted DEV leaderboard snapshot {job.pk}: {len(rows)} eligible runs."}
    if any('"' in value or '\n' in value or '\r' in value for value in fields.values()):
        raise ValueError("Invalid Workshop configuration value.")
    (target / "upload.vdf").write_text('"workshopitem"\n{\n' + ''.join(f'"{k}" "{v}"\n' for k, v in fields.items()) + '}\n', encoding="utf-8")
    hashes = {file.relative_to(target / "Contents").as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
              for file in sorted((target / "Contents").rglob("*")) if file.is_file()}
    (target / "sha256.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    return target


def steam(executable, username, arguments):
    return subprocess.run(
        [str(executable), "+login", username, *arguments, "+quit"],
        cwd=executable.parent, stdin=subprocess.DEVNULL, capture_output=True,
        timeout=settings.LEADERBOARD_UPLOAD_TIMEOUT, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def verified_download(executable, target):
    downloaded = executable.parent / "steamapps/workshop/content/108600" / TEST_ITEM_ID
    expected = json.loads((target / "sha256.json").read_text(encoding="utf-8"))
    actual = {p.relative_to(downloaded).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in downloaded.rglob("*") if p.is_file()}
    if actual != expected:
        raise ValueError("Downloaded Workshop package does not match the generated snapshot.")


def download_and_verify(executable, username, target):
    download = steam(executable, username, ["+workshop_download_item", "108600", TEST_ITEM_ID, "validate"])
    if download.returncode != 0 or b"success. downloaded item" not in download.stdout.lower():
        raise RuntimeError("Workshop download did not complete.")
    verified_download(executable, target)


def reconcile(job_id):
    executable, username, root = configuration()
    with steam_lock(executable):
        job = Job.objects.get(
            pk=job_id, status__in=(Job.Status.RUNNING, Job.Status.UNCERTAIN),
        )
        target = root / f"job-{job.pk}"
        if job.status == Job.Status.RUNNING and not job.package_path:
            # Publication saves the package path before it invokes SteamCMD.
            job.status = Job.Status.FAILED
            job.summary = "Reconciled an interruption before SteamCMD upload."
        else:
            if job.item_id != TEST_ITEM_ID or Path(job.package_path).resolve() != target.resolve():
                raise ValueError("The job does not have a retained upload package.")
            download_and_verify(executable, username, target)
            job.status = Job.Status.PUBLISHED
            job.summary = "Reconciled against the Unlisted test item; downloaded hashes verified."
        job.finished_at = timezone.now()
        job.save(update_fields=("status", "summary", "finished_at"))
        return job


def publish(job):
    uploading = False
    try:
        executable, username, root = configuration()
        rows = snapshot()
        job.item_id = TEST_ITEM_ID
        job.row_count = len(rows)
        job.content_hash = data_hash(rows)
        previous = Job.objects.filter(status=Job.Status.PUBLISHED, item_id=TEST_ITEM_ID).order_by("-finished_at").first()
        if previous and previous.content_hash == job.content_hash:
            job.status = Job.Status.UNCHANGED
            job.summary = "Standings and mod template are unchanged; no upload needed."
        else:
            target = package(job, rows, root)
            job.package_path = str(target)
            job.summary = "Package prepared. Upload and download verification in progress."
            job.save()
            uploading = True
            result = steam(executable, username, ["+workshop_build_item", str(target / "upload.vdf")])
            output = (result.stdout + result.stderr).decode(errors="replace").lower()
            if "committing update...success" not in output:
                if any(marker in output for marker in ("invalid password", "steam guard", "account logon denied", "account login denied", "cached credentials not found")):
                    uploading = False
                    job.status = Job.Status.AUTH_REQUIRED
                    job.summary = "Steam owner authentication is required on the DEV host."
                else:
                    raise RuntimeError("Steam did not confirm the upload; review before retrying.")
            elif result.returncode != 0:
                raise RuntimeError("Steam reported an abnormal exit after upload; review before retrying.")
            else:
                download_and_verify(executable, username, target)
                job.status = Job.Status.PUBLISHED
                job.summary = f"Published {len(rows)} DEV standings to the Unlisted test item; downloaded hashes verified."
    except Exception as exc:
        job.status = Job.Status.UNCERTAIN if uploading else Job.Status.FAILED
        # Store controlled summaries only, never raw Steam authentication output.
        job.summary = f"{'Upload needs reconciliation' if uploading else 'Publication stopped before upload'} ({type(exc).__name__})."
    job.finished_at = timezone.now()
    job.save()
    if job.status in (Job.Status.FAILED, Job.Status.AUTH_REQUIRED, Job.Status.UNCERTAIN):
        try:
            notify_superusers("Daily leaderboard publication needs attention", f"Job {job.pk}: {job.summary}")
        except Exception:
            logger.exception("Unable to notify moderators about leaderboard job %s.", job.pk)
    return job
