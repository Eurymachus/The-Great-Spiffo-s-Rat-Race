import os
import threading
import uuid

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


HEARTBEAT_CACHE_KEY = "operations:reference-worker:heartbeat"


def record_worker_heartbeat(worker_id):
    cache.set(
        HEARTBEAT_CACHE_KEY,
        {
            "worker_id": worker_id,
            "recorded_at": timezone.now().isoformat(),
            "release_id": getattr(settings, "RELEASE_ID", "development"),
            "process_id": os.getpid(),
        },
        timeout=settings.REFERENCE_WORKER_HEARTBEAT_TTL_SECONDS,
    )


class WorkerHeartbeat:
    def __init__(self):
        self.worker_id = uuid.uuid4().hex
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._run,
            name="reference-worker-heartbeat",
            daemon=True,
        )

    def _run(self):
        while not self.stop_event.is_set():
            record_worker_heartbeat(self.worker_id)
            self.stop_event.wait(settings.REFERENCE_WORKER_HEARTBEAT_INTERVAL_SECONDS)

    def start(self):
        record_worker_heartbeat(self.worker_id)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)
        current = cache.get(HEARTBEAT_CACHE_KEY)
        if current and current.get("worker_id") == self.worker_id:
            cache.delete(HEARTBEAT_CACHE_KEY)
