import threading
import time
from datetime import timedelta
from typing import List, Optional

from src.execution.worker.execution_worker import ExecutionWorker


class WorkerSupervisor:
    """
    Lightweight in-process supervisor.
    Restarts dead worker threads and supports graceful stop.
    """

    def __init__(self, workers: List[ExecutionWorker]):
        self.workers = workers
        self._threads: List[threading.Thread] = []
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        self._threads = []
        for worker in self.workers:
            thread = threading.Thread(target=worker.run_forever, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop_event.set()
        for worker in self.workers:
            worker.stop()
        for thread in self._threads:
            thread.join(timeout=2.0)
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=2.0)

    def run_watchdog(self, interval_seconds: float = 1.0) -> None:
        while not self._stop_event.is_set():
            for idx, thread in enumerate(list(self._threads)):
                if thread.is_alive():
                    continue
                replacement = threading.Thread(target=self.workers[idx].run_forever, daemon=True)
                replacement.start()
                self._threads[idx] = replacement
            for worker in self.workers:
                stale = worker.heartbeat_store.stale_workers(
                    timedelta(seconds=max(1, worker.config.visibility_timeout_seconds))
                )
                if stale:
                    worker.queue.reclaim_expired()
            time.sleep(interval_seconds)

    def start_watchdog(self, interval_seconds: float = 1.0) -> None:
        self._watchdog_thread = threading.Thread(
            target=self.run_watchdog,
            kwargs={"interval_seconds": interval_seconds},
            daemon=True,
        )
        self._watchdog_thread.start()
