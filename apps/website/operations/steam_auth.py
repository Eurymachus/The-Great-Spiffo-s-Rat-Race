import queue
import re
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings


SAFE_ACCOUNT = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
SAFE_GUARD_CODE = re.compile(r"^[A-Za-z0-9]{4,12}$")
GUARD_REQUIRED = (
    "steam guard",
    "two-factor",
    "auth code",
    "enter the current code",
)
LOGIN_OK = ("logged in ok", "waiting for user info...ok")
LOGIN_FAILED = (
    "invalid password",
    "account logon denied",
    "account login denied",
    "failed",
)
_attempts = {}
_lock = threading.Lock()


@dataclass
class PendingAuthentication:
    account_name: str
    process: object
    executable: str = ""
    uses_pty: bool = False
    output: queue.Queue = field(default_factory=queue.Queue)
    expires_at: float = 0
    reader: threading.Thread | None = None
    captured: bytearray = field(default_factory=bytearray)
    next_cache_check: float = 0

    def destroy(self):
        if self.uses_pty:
            try:
                if self.process.isalive():
                    self.process.terminate(force=True)
            except Exception:
                pass
        else:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
            except OSError:
                pass
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
        self.captured[:] = b"\0" * len(self.captured)


def _quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _read_output(attempt):
    stream = None if attempt.uses_pty else attempt.process.stdout
    if not attempt.uses_pty and not stream:
        return
    while True:
        try:
            chunk = (
                attempt.process.read(1).encode(errors="replace")
                if attempt.uses_pty
                else stream.read(1)
            )
        except (EOFError, OSError):
            return
        except Exception:
            if attempt.uses_pty and not attempt.process.isalive():
                return
            raise
        if not chunk:
            return
        attempt.output.put(chunk)


def _start_session(executable, account_name, password):
    if not SAFE_ACCOUNT.fullmatch(account_name):
        raise ValueError("Enter a valid Steam account login name.")
    uses_pty = os.name == "nt"
    if uses_pty:
        try:
            from winpty import PtyProcess
        except ImportError as exc:
            raise RuntimeError(
                "Windows Steam authentication requires pywinpty."
            ) from exc
        process = PtyProcess.spawn([str(Path(executable))])
    else:
        process = subprocess.Popen(
            [str(Path(executable))],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    attempt = PendingAuthentication(
        account_name=account_name,
        process=process,
        executable=str(Path(executable)),
        uses_pty=uses_pty,
        expires_at=time.monotonic() + 300,
        next_cache_check=time.monotonic() + 2,
    )
    attempt.reader = threading.Thread(
        target=_read_output,
        args=(attempt,),
        daemon=True,
        name="steamcmd-auth-output",
    )
    attempt.reader.start()
    command = f"login {_quote(account_name)} {_quote(password)}"
    _write(attempt, command)
    command = "\0" * len(command)
    return attempt


def _write(attempt, value):
    if attempt.uses_pty:
        attempt.process.write(f"{value}\r\n")
    else:
        payload = f"{value}\n".encode()
        attempt.process.stdin.write(payload)
        attempt.process.stdin.flush()
        payload = b"\0" * len(payload)


def _status_from_output(attempt):
    while True:
        try:
            attempt.captured.extend(attempt.output.get_nowait())
        except queue.Empty:
            break
    output = attempt.captured.decode(errors="replace").casefold()
    if any(marker in output for marker in LOGIN_OK):
        return "authenticated"
    if any(marker in output for marker in GUARD_REQUIRED):
        return "guard_required"
    if any(marker in output for marker in LOGIN_FAILED):
        return "failed"
    process_finished = (
        not attempt.process.isalive()
        if attempt.uses_pty
        else attempt.process.poll() is not None
    )
    if process_finished:
        return "failed"
    return "waiting"


def _wait_for_status(attempt, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = _status_from_output(attempt)
        if status != "waiting":
            return status
        time.sleep(0.05)
    return _status_from_output(attempt)


def _finish(attempt):
    try:
        process_running = (
            attempt.process.isalive()
            if attempt.uses_pty
            else attempt.process.poll() is None
        )
        if process_running:
            _write(attempt, "quit")
    except (BrokenPipeError, OSError, EOFError):
        pass
    finally:
        attempt.destroy()


def begin_authentication(executable, account_name, password):
    attempt = _start_session(executable, account_name, password)
    status = _wait_for_status(attempt, settings.STEAMCMD_AUTH_TIMEOUT_SECONDS)
    if status == "authenticated":
        _finish(attempt)
        return "authenticated", ""
    if status == "guard_required":
        token = uuid.uuid4().hex
        with _lock:
            _purge_expired()
            _attempts[token] = attempt
        return "guard_required", token
    _finish(attempt)
    return "failed", ""


def complete_authentication(executable, token, guard_code):
    del executable  # The existing authenticated SteamCMD process is authoritative.
    code = guard_code.strip()
    if not SAFE_GUARD_CODE.fullmatch(code):
        return False
    with _lock:
        _purge_expired()
        attempt = _attempts.pop(token, None)
    if not attempt:
        return False
    try:
        # A Steam Mobile approval can complete the existing process while the
        # operator is viewing this form. Do not send the typed code as a
        # SteamCMD command if approval has already succeeded.
        current_status = _wait_for_status(attempt, 1)
        if current_status == "authenticated":
            return True
        if current_status == "failed":
            return False
        _write(attempt, code)
        status = _wait_for_status(attempt, settings.STEAMCMD_AUTH_TIMEOUT_SECONDS)
        return status == "authenticated"
    finally:
        _finish(attempt)


def _cached_session_valid(executable, account_name):
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [executable, "+login", account_name, "+quit"],
            capture_output=True,
            timeout=settings.STEAMCMD_AUTH_TIMEOUT_SECONDS,
            creationflags=creationflags,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    output = (completed.stdout + completed.stderr).decode(
        errors="replace"
    ).casefold()
    return completed.returncode == 0 and all(
        marker in output
        for marker in ("logging in using cached credentials", "waiting for user info...ok")
    )


def poll_authentication(token):
    with _lock:
        _purge_expired()
        attempt = _attempts.get(token)
    if not attempt:
        return "expired"
    status = _status_from_output(attempt)
    if status in {"waiting", "guard_required"}:
        now = time.monotonic()
        if now < attempt.next_cache_check:
            return "waiting"
        attempt.next_cache_check = now + 5
        if not _cached_session_valid(attempt.executable, attempt.account_name):
            return "waiting"
        status = "authenticated"
    with _lock:
        _attempts.pop(token, None)
    _finish(attempt)
    return status


def _purge_expired():
    now = time.monotonic()
    for token, attempt in list(_attempts.items()):
        if attempt.expires_at <= now:
            attempt.destroy()
            del _attempts[token]
