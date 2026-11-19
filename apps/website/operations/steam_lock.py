"""Process-wide exclusion for application jobs using one SteamCMD installation."""
import os
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class SteamBusy(OSError):
    pass


@contextmanager
def steam_lock(executable):
    lock_path = Path(executable).resolve().parent / "tgsrr-steamcmd.lock"
    with lock_path.open("a+b") as lock:
        lock.seek(0)
        try:
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise SteamBusy("SteamCMD is busy with another operation.") from exc
        yield
