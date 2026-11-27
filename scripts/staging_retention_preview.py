"""Fixed staging retention previews. Report only validated aggregate output."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from host_artifacts import checked, eligible, read_environment

ROOT = Path(r"G:\RatRace_Staging")
COMMANDS = {
    "apply_account_retention": (
        r"Candidates: \d+; eligible: \d+; blocked: \d+; deleted: 0\.",
        r"Preview only\. Pending file deletions: \d+\.",
    ),
    "apply_evidence_retention": (
        r"Preview only: eligible=\d+, retained=\d+, held=\d+, changed=\d+, blocked=\d+, empty=\d+",
    ),
    "prune_runtime_state": (r"Preview only: \d+ expired rate-limit bucket\(s\)\.",),
}
CHILD = """
import sys
def reject_external_operations(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname",
                 "subprocess.Popen", "os.system"}:
        raise RuntimeError("External operation blocked in retention preview.")
sys.addaudithook(reject_external_operations)
import django
django.setup()
from django.db import connection, transaction
from django.core.management import call_command
with transaction.atomic(), connection.cursor() as cursor:
    cursor.execute("SET TRANSACTION READ ONLY")
    cursor.execute(
        "SELECT current_user,current_database(),inet_server_port(),host(inet_server_addr()),"
        "current_setting('transaction_read_only'),rolsuper FROM pg_roles WHERE rolname=current_user"
    )
    if cursor.fetchone() != ('ratrace', 'ratrace', 5433, '127.0.0.1', 'on', False):
        raise RuntimeError("Wrong staging database identity.")
    call_command(sys.argv[1], apply=False)
"""


def staging_environment(root, release):
    values = read_environment(root / "config/staging.env")
    expected = {
        "DJANGO_SETTINGS_MODULE": "config.settings_windows_staging",
        "POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "ratrace", "POSTGRES_USER": "ratrace", "RELEASE_ID": release,
    }
    if any(values.get(key) != value for key, value in expected.items()):
        raise ValueError("Wrong staging configuration.")
    safe_values = {key: value for key, value in values.items() if not key.startswith(("PG", "PYTHON"))}
    environment = {key: value for key, value in os.environ.items() if key.upper() in {
        "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "PATH", "COMSPEC", "TEMP", "TMP",
    }}
    return {**environment, **safe_values, "PGOPTIONS": "-c default_transaction_read_only=on",
            "PGCONNECT_TIMEOUT": "5", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}


def run_preview(command, website, environment):
    result = subprocess.run(
        [sys.executable, "-B", "-c", CHILD, command], cwd=website, env=environment,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    lines = result.stdout.splitlines()
    patterns = COMMANDS[command]
    if result.returncode or len(lines) != len(patterns) or any(
        not re.fullmatch(pattern, line) for pattern, line in zip(patterns, lines)
    ):
        return {"result": "failed", "exit": result.returncode}
    review = any(re.search(r"\b(?:blocked[:=]\s*|changed=|Pending file deletions: )[1-9]", line) for line in lines)
    return {"result": "review" if review else "success", "counts": lines}


def collect_previews(root, release):
    website = checked(root / "releases" / release / "apps/website")
    if not checked(website / "manage.py").is_file():
        raise ValueError("Deployed website missing.")
    environment = staging_environment(root, release)
    results = {}
    for command in COMMANDS:
        try:
            results[command] = run_preview(command, website, environment)
        except (OSError, subprocess.SubprocessError):
            results[command] = {"result": "failed"}
    for name, path in (("backups", root / "backups"), ("routine_logs", root / "logs/routine")):
        try:
            results[name] = {"result": "success", "eligible": len(eligible(path))}
        except (OSError, ValueError, TypeError, KeyError):
            results[name] = {"result": "failed"}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{7,40}", args.release):
        parser.error("Invalid release.")
    try:
        results = collect_previews(checked(ROOT), args.release)
    except (OSError, ValueError):
        results = {"preflight": {"result": "failed"}}
    print(json.dumps(results))
    return int(any(item["result"] != "success" for item in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
