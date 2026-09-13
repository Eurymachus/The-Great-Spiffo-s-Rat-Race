"""Data-only single-slot deployment protocol. Installed directory is admin controlled."""
import contextlib
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import staging_release as release


@contextlib.contextmanager
def exclusive_request(path, write=False):
    """OPEN_EXISTING, no sharing: writers and rename/delete cannot race consumption."""
    import msvcrt
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                  ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    handle = kernel.CreateFileW(str(path), 0x40000000 if write else 0x80000000,
                                0, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "Deployment request busy or inaccessible")
    fd = msvcrt.open_osfhandle(handle, os.O_WRONLY if write else os.O_RDONLY)
    with os.fdopen(fd, "wb" if write else "rb") as stream:
        yield stream


def request(data):
    if len(data) > 256:
        raise ValueError("Request too large")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate request field")
            value[key] = item
        return value
    value = json.loads(data, object_pairs_hook=unique)
    if not isinstance(value, dict) or set(value) != {"schema", "sequence", "commit"}:
        raise ValueError("Only schema, sequence and commit are accepted")
    if type(value["schema"]) is not int or value["schema"] != 1:
        raise ValueError("Unknown request schema")
    if type(value["sequence"]) is not int or not 1 <= value["sequence"] <= 2**53:
        raise ValueError("Invalid request sequence")
    if not isinstance(value["commit"], str) or not re.fullmatch("[0-9a-f]{40}", value["commit"]):
        raise ValueError("A full hexadecimal commit is required")
    return value


def result(root, value):
    # Directory is staging-write/operator-read. Replacement never inherits inbox ACLs.
    target = root / "control/result/status.json"
    temporary = target.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    for attempt in range(50):
        try:
            os.replace(temporary, target)
            break
        except PermissionError:
            if attempt == 49:
                raise
            time.sleep(0.1)  # A read-only status viewer may briefly deny delete sharing.


def consume(root, stream, deploy):
    old = release.read_json(root / "control/result/status.json")
    if old["status"] == "running":
        result(root, dict(old, status="failed", error="Interrupted deployment; inspect active release before resubmitting"))
        return
    try:
        value = request(stream.read(257))
    except (ValueError, UnicodeError):
        result(root, dict(schema=1, sequence=old["next_sequence"], next_sequence=old["next_sequence"] + 1,
                          status="rejected", error="Malformed deployment request"))
        raise
    if value["sequence"] != old["next_sequence"]:
        raise ValueError("Stale or replayed request")
    status = dict(schema=1, sequence=value["sequence"], next_sequence=value["sequence"] + 1,
                  commit=value["commit"], status="running")
    result(root, status)  # Durably consume identity before any side effect.
    try:
        selected = deploy(value["commit"])
        result(root, dict(status, status="succeeded", verified=selected))
    except Exception:
        # Detailed diagnostics stay in protected logs, not the operator data channel.
        result(root, dict(status, status="failed", error="Deployment failed; administrator should inspect deployment log and rollback state"))
        raise


def deploy(commit):
    root = release.ROOT
    if Path(sys.prefix).resolve() != (root / "venv").resolve():
        raise RuntimeError("Staging virtual environment needs administrator repair after relocation")
    repository = root / "repository.git"
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA"}}
    env.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    git = ["git", "-c", "credential.helper=", "-c", "core.fsmonitor=false"]
    token = root / "config/git-token"
    if token.exists():
        import base64
        credential = base64.b64encode(("x-access-token:" + token.read_text().strip()).encode()).decode()
        env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                   GIT_CONFIG_VALUE_0="Authorization: Basic " + credential)
    if not (repository / "HEAD").exists():
        subprocess.run([*git, "init", "--bare", str(repository)], env=env, check=True)
    # Fixed repository and fixed branch. Requests cannot supply Git options or paths.
    subprocess.run([*git, "-C", str(repository), "fetch",
                    "https://github.com/Eurymachus/The-Great-Spiffo-s-Rat-Race.git",
                    "refs/heads/codex/rat-race-dev:refs/remotes/origin/codex/rat-race-dev"], env=env, check=True)
    subprocess.run([*git, "-C", str(repository), "merge-base", "--is-ancestor",
                    commit, "refs/remotes/origin/codex/rat-race-dev"], env=env, check=True)
    name = commit[:12]
    if not (root / "releases" / name).exists():
        release.publish(root, repository, commit)
    selected, _ = release.release(root, name)
    if selected["commit"] != commit:
        raise ValueError("Release identity collision")
    operation = release.switch if (root / "state/active-release.json").exists() else release.initialize
    return operation(root, name, release.WindowsHost(root))


def main():
    if len(sys.argv) != 2 or sys.argv[1] != "process":
        raise ValueError("Only the fixed process operation is supported")
    root = release.ROOT
    with release.switch_lock(root):
        with exclusive_request(root / "control/inbox/request.json") as stream:
            consume(root, stream, deploy)


if __name__ == "__main__":
    main()
