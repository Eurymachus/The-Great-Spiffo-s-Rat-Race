"""Fixed-scope Windows staging launcher and transactional release switch.

Only the CLI binds the real staging root. Tests inject a temporary root and OS adapter.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time
import zipfile
import tempfile
import urllib.request
from datetime import datetime, timezone

ROOT = Path(r"G:\RatRace_StagingSecured")
TASKS = ("RatRaceStagingWeb", "RatRaceStagingWorker")
MANIFEST = "staging-release.json"


def confined(path, parent):
    path, parent = Path(path).absolute(), Path(parent).absolute()
    if ".." in path.parts or not path.is_relative_to(parent) or path == parent:
        raise ValueError("Path is outside the staging scope")
    # Reject junctions as well as symlinks, including ancestors of the root.
    for item in (path, *path.parents):
        if item.exists() and (item.is_symlink() or getattr(item.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Reparse points are not allowed in staging paths")
    if not path.resolve().is_relative_to(parent.resolve()):
        raise ValueError("Resolved path is outside staging")
    return path


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("Manifest must be an object")
    return value


def publish(root, repository, revision):
    """Export committed Git content only, never a mutable working directory."""
    commit = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "--verify", revision + "^{commit}"], text=True).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid Git commit identity")
    releases = confined(root / "releases", root)
    releases.mkdir(exist_ok=True)
    name = commit[:12]
    destination = confined(releases / name, releases)
    if destination.exists():
        raise ValueError("Immutable release already exists")
    archive = subprocess.check_output(["git", "-C", str(repository), "archive", "--format=zip", commit])
    with tempfile.TemporaryDirectory(prefix=".publish-", dir=releases) as temporary:
        directory = Path(temporary)
        hashes = {}
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            for item in source.infolist():
                target = confined(directory / item.filename, directory)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if (item.external_attr >> 16) & 0o170000 == 0o120000 or item.filename == MANIFEST:
                    raise ValueError("Release archive contains a symlink or reserved manifest")
                target.parent.mkdir(parents=True, exist_ok=True)
                data = source.read(item)
                target.write_bytes(data)
                hashes[item.filename] = hashlib.sha256(data).hexdigest()
        (directory / MANIFEST).write_text(json.dumps({"schema": 1, "commit": commit, "files": hashes}, sort_keys=True), encoding="utf-8")
        directory.rename(destination)
    release(root, name)
    return name


def release(root, name):
    if not re.fullmatch(r"[0-9a-f]{7,40}", name):
        raise ValueError("Release must be a short hexadecimal commit, not a path")
    directory = confined(root / "releases" / name, root / "releases")
    manifest = read_json(confined(directory / MANIFEST, directory))
    commit = manifest.get("commit", "")
    files = manifest.get("files")
    if manifest.get("schema") != 1 or not re.fullmatch(r"[0-9a-f]{40}", commit) or not commit.startswith(name):
        raise ValueError("Release manifest commit does not match directory identity")
    if not isinstance(files, dict) or not files:
        raise ValueError("Missing release file hashes")
    required = {"apps/website/manage.py", "apps/website/config/asgi.py", "apps/website/config/settings_windows_staging.py"}
    if not required.issubset(files):
        raise ValueError("Incomplete website release")
    actual = set()
    for item in directory.rglob("*"):
        confined(item, directory)
        if item.is_file() and item != directory / MANIFEST:
            actual.add(item.relative_to(directory).as_posix())
    if actual != set(files):
        raise ValueError("Release file inventory differs from its manifest")
    for relative, digest in files.items():
        item = confined(directory / relative, directory)
        if not isinstance(digest, str) or hashlib.sha256(item.read_bytes()).hexdigest() != digest:
            raise ValueError("Release file hash mismatch")
    return {"schema": 1, "release": name, "commit": commit}, directory


def active(root):
    pointer = read_json(confined(root / "state" / "active-release.json", root))
    selected, directory = release(root, pointer.get("release", ""))
    if pointer != selected:
        raise ValueError("Active pointer does not match release manifest")
    return selected, directory


def atomic_pointer(root, value):
    directory = confined(root / "state", root)
    directory.mkdir(exist_ok=True)
    target = confined(directory / "active-release.json", root)
    temporary = directory / ("pointer-" + os.urandom(12).hex() + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def switch_lock(root):
    import msvcrt
    path = confined(root / "state" / "switch.lock", root)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("Another staging switch is in progress") from exc
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def environment(root, selected):
    system_keys = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "COMSPEC", "PATHEXT", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE"}
    env = {key: value for key, value in os.environ.items() if key.upper() in system_keys}
    for line in confined(root / "config" / "staging.env", root).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("Malformed staging environment")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        env[key] = value
    if env.get("DJANGO_SETTINGS_MODULE") != "config.settings_windows_staging":
        raise ValueError("Staging settings module is required")
    if env.get("POSTGRES_HOST") not in {"127.0.0.1", "localhost"} or env.get("POSTGRES_PORT") != "5433":
        raise ValueError("Staging PostgreSQL must be loopback port 5433")
    for key in ("MEDIA_ROOT", "AVATAR_QUARANTINE_ROOT", "PZ_REFERENCE_ROOT"):
        if not env.get(key):
            raise ValueError("Missing staging storage setting: " + key)
        confined(Path(env[key]), root)
    env.update(RELEASE_ID=selected["commit"], RUNTIME_STATE_BACKEND="database", PYTHONDONTWRITEBYTECODE="1")
    env["STATIC_ROOT"] = str(confined(root / "runtime" / "static" / selected["commit"], root))
    # Do not allow an operator's shell to inject code into the fixed interpreter.
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


class WindowsHost:
    def __init__(self, root):
        self.root = root
        self.python = confined(root / "venv" / "Scripts" / "python.exe", root)

    def control(self, operation):
        command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
                   str(Path(__file__).with_name("Staging-TaskControl.ps1")), "-Operation", operation]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("Staging task control failed: " + result.stderr.strip())
        return json.loads(result.stdout) if result.stdout.strip() else None

    def preflight(self):
        self.control("Validate")

    def prepare(self, selected, directory):
        env = environment(self.root, selected)
        Path(env["STATIC_ROOT"]).mkdir(parents=True, exist_ok=True)
        for args in (("migrate", "--noinput"), ("bootstrap_roles",), ("collectstatic", "--noinput"),
                     ("check", "--deploy", "--fail-level", "WARNING"), ("check_production_deployment",)):
            subprocess.run([str(self.python), "manage.py", *args], cwd=directory / "apps/website", env=env, check=True)

    def stop(self):
        self.control("Stop")

    def start(self):
        self.control("Start")

    def verify(self, selected, directory, started):
        env = environment(self.root, selected)
        deadline = time.monotonic() + 180
        last_error = "No health response"
        while time.monotonic() < deadline:
            try:
                processes = self.control("Verify")
                request = urllib.request.Request("http://127.0.0.1:8002/health/ready/", headers={"X-Forwarded-Proto": "https"})
                # Ignore proxy variables and do not follow redirects to another service.
                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, *args):
                        return None
                with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=5) as response:
                    health = json.load(response)
                    if response.status != 200 or health.get("release") != selected["commit"] or not health.get("checks", {}).get("reference_worker"):
                        raise RuntimeError("Readiness release or worker check mismatch")
                code = "import django,json;django.setup();from operations.runtime_state import get_worker_heartbeat_state;print(json.dumps(get_worker_heartbeat_state()))"
                result = subprocess.run([str(self.python), "-c", code], cwd=directory / "apps/website", env=env, capture_output=True, text=True, check=True, timeout=15)
                heartbeat = json.loads(result.stdout)
                if not heartbeat or heartbeat.get("release_id") != selected["commit"] or int(heartbeat.get("process_id", 0)) != processes["worker_pid"]:
                    raise RuntimeError("Worker heartbeat does not belong to selected runtime")
                if datetime.fromisoformat(heartbeat["recorded_at"]) < started:
                    raise RuntimeError("Worker heartbeat predates cutover")
                return
            except Exception as exc:
                last_error = str(exc)
                time.sleep(2)
        raise RuntimeError("Cutover verification failed: " + last_error)


def switch(root, name, host):
    selected, directory = release(root, name)
    previous, previous_directory = active(root)  # Initial pointer is installed separately.
    host.preflight()
    host.prepare(selected, directory)
    # Revalidate after preparation, before changing any running process or pointer.
    release(root, name)
    try:
        host.stop()
        atomic_pointer(root, selected)
        started = datetime.now(timezone.utc)
        host.start()
        host.verify(selected, directory, started)
    except Exception as failure:
        try:
            host.stop()
            atomic_pointer(root, previous)
            started = datetime.now(timezone.utc)
            host.start()
            host.verify(previous, previous_directory, started)
        except Exception as rollback:
            raise RuntimeError(f"Cutover failed ({failure}); ROLLBACK FAILED ({rollback}). Operator intervention required.") from rollback
        raise RuntimeError(f"Cutover failed; previous release restored: {failure}") from failure
    return selected


def initialize(root, name, host):
    if (root / "state/active-release.json").exists():
        raise RuntimeError("Existing pointer must be changed with switch")
    selected, directory = release(root, name)
    host.preflight()
    host.prepare(selected, directory)
    release(root, name)
    host.stop()
    atomic_pointer(root, selected)
    try:
        host.start()
        host.verify(selected, directory, datetime.now(timezone.utc))
    except Exception:
        host.stop()
        (root / "state/active-release.json").unlink()
        raise
    return selected


def run(role):
    selected, directory = active(ROOT)
    env = environment(ROOT, selected)
    os.environ.clear()
    os.environ.update(env)
    os.chdir(directory / "apps/website")
    sys.path.insert(0, str(Path.cwd()))
    if role == "Web":
        import uvicorn
        uvicorn.run("config.asgi:application", host="127.0.0.1", port=8002, proxy_headers=True, forwarded_allow_ips="127.0.0.1")
    else:
        sys.argv = ["manage.py", "run_reference_update_worker"]
        runpy.run_path("manage.py", run_name="__main__")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("switch").add_argument("release")
    sub.add_parser("validate").add_argument("release")
    sub.add_parser("initialize").add_argument("release")
    export = sub.add_parser("publish")
    export.add_argument("repository")
    export.add_argument("commit")
    sub.add_parser("run").add_argument("--role", choices=("Web", "Worker"), required=True)
    args = parser.parse_args()
    if args.command == "run":
        run(args.role)
    elif args.command == "validate":
        print(json.dumps(release(ROOT, args.release)[0]))
    elif args.command == "publish":
        print(publish(ROOT, args.repository, args.commit))
    else:
        with switch_lock(ROOT):
            if args.command == "initialize":
                if (ROOT / "state/active-release.json").exists():
                    raise RuntimeError("Existing pointer must be changed with switch")
                selected, directory = release(ROOT, args.release)
                host = WindowsHost(ROOT)
                host.preflight()
                host.prepare(selected, directory)
                host.stop()
                atomic_pointer(ROOT, selected)
                try:
                    started = datetime.now(timezone.utc)
                    host.start()
                    host.verify(selected, directory, started)
                except Exception:
                    host.stop()
                    (ROOT / "state/active-release.json").unlink()
                    raise
            else:
                print(json.dumps(switch(ROOT, args.release, WindowsHost(ROOT))))


if __name__ == "__main__":
    main()
