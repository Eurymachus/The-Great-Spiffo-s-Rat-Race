"""Capture tool output while keeping a bounded live tail for administrators."""

import re
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime

from .models import ReferenceUpdateJob


LOG_LIMIT = 65536
PROGRESS = re.compile(r"Update state .*?progress:\s*([\d.]+)", re.I)


def steam_console_progress(executable, started_at):
    """Read only this job's timestamped progress, never login/session output."""
    if not started_at:
        return ""
    path = Path(executable).parent / "logs" / "console_log.txt"
    try:
        with path.open("rb") as stream:
            end = stream.seek(0, 2)
            stream.seek(max(0, end - LOG_LIMIT))
            tail = stream.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    lines = []
    for line in tail.splitlines():
        match = re.fullmatch(r"\[([^]]+)\]\s+(Update state .+)", line)
        if not match:
            continue
        try:
            timestamp = datetime.strptime(match[1], "%Y-%m-%d %H:%M:%S").astimezone()
        except ValueError:
            continue
        if timestamp >= started_at:
            lines.append(line)
    return "\n".join(lines)


def run_logged_process(arguments, *, job, timeout, label, redact=()):
    def publish(output):
        output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", output).replace("\r", "\n")
        for value in redact:
            if value:
                output = output.replace(value, "[account]")
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        latest = lines[-1] if lines else label
        match = PROGRESS.search(latest)
        ReferenceUpdateJob.objects.filter(pk=job.pk).update(
            log_output=output[-LOG_LIMIT:],
            progress_message=latest[:300],
            progress_percent=min(100, max(0, float(match[1]))) if match else None,
        )

    publish("")
    # A file avoids pipe deadlocks and handles output without newline delimiters.
    with tempfile.TemporaryDirectory(prefix="tgsrr-job-") as directory:
        output_path = Path(directory) / "output.log"
        with output_path.open("wb") as writer, output_path.open("rb") as reader:
            with subprocess.Popen(
                arguments, stdin=subprocess.DEVNULL, stdout=writer,
                stderr=subprocess.STDOUT,
            ) as process:
                started = time.monotonic()
                output = ""
                try:
                    while True:
                        returncode = process.poll()
                        end = reader.seek(0, 2)
                        reader.seek(max(0, end - LOG_LIMIT))
                        output = reader.read().decode("utf-8", errors="replace")
                        reader.seek(0, 2)
                        publish(output)
                        if returncode is not None:
                            break
                        if time.monotonic() - started >= timeout:
                            raise subprocess.TimeoutExpired(arguments, timeout)
                        time.sleep(1)
                except BaseException:
                    process.kill()
                    process.wait()
                    raise
    return subprocess.CompletedProcess(arguments, returncode, stdout=output, stderr="")
