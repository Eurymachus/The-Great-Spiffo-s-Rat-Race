"""Private, per-process cooperative stop requests from the host launcher."""
import os
from pathlib import Path


def stop_requested():
    filename = os.environ.get("RR_PROCESS_STOP_FILE")
    token = os.environ.get("RR_PROCESS_STOP_TOKEN")
    if not filename or not token:
        return False
    try:
        return Path(filename).read_text(encoding="utf-8-sig").strip() == token
    except FileNotFoundError:
        return False
