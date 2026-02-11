import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional

from src.execution.results.execution_result_inbox import ExecutionResultInbox
from src.execution.logging.structured_runtime_logger import StructuredRuntimeLogger


@dataclass(frozen=True)
class ResultDispatcherConfig:
    dispatcher_id: str
    batch_size: int = 50
    poll_interval_seconds: float = 0.2
    visibility_timeout_seconds: int = 10
    result_apply_sla_ms: int = 1000


class ResultDispatcherService:
    """
    Hybrid push+poll dispatcher:
    - push path: notify() wakes the dispatcher immediately
    - poll path: periodic leasing handles missed notifications
    """

    def __init__(
        self,
        config: ResultDispatcherConfig,
        inbox: ExecutionResultInbox,
        apply_result: Callable[[dict], None],
        structured_logger: Optional[StructuredRuntimeLogger] = None,
    ):
        self.config = config
        self.inbox = inbox
        self.apply_result = apply_result
        self.structured_logger = structured_logger
        self._notify_event = threading.Event()
        self._stop_event = threading.Event()
        self._sla_violations: List[float] = []

    def notify(self) -> None:
        self._notify_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._notify_event.set()

    def run_forever(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._notify_event.wait(timeout=self.config.poll_interval_seconds)
            self._notify_event.clear()

    def run_once(self) -> int:
        self.inbox.reclaim_expired()
        leased = self.inbox.lease(
            consumer_id=self.config.dispatcher_id,
            batch=self.config.batch_size,
            visibility_timeout=timedelta(seconds=self.config.visibility_timeout_seconds),
        )
        applied = 0
        for envelope in leased:
            if self._stop_event.is_set():
                break
            self._apply_one(envelope)
            self.inbox.ack(envelope["id"], self.config.dispatcher_id)
            applied += 1
        return applied

    def sla_violations(self) -> List[float]:
        return list(self._sla_violations)

    def _apply_one(self, envelope: dict) -> None:
        now = datetime.now(timezone.utc)
        latency_ms = (now - envelope["received_at"]).total_seconds() * 1000.0
        if latency_ms > self.config.result_apply_sla_ms:
            self._sla_violations.append(latency_ms)
            self._log(
                "DISPATCHER_SLA_VIOLATION",
                dispatcher_id=self.config.dispatcher_id,
                job_id=str(envelope.get("job_id")),
                intent_id=str(envelope.get("intent_id")),
                context_domain=envelope.get("context_domain"),
                latency_ms=latency_ms,
            )
        else:
            self._log(
                "DISPATCHER_APPLY",
                dispatcher_id=self.config.dispatcher_id,
                job_id=str(envelope.get("job_id")),
                intent_id=str(envelope.get("intent_id")),
                context_domain=envelope.get("context_domain"),
                latency_ms=latency_ms,
            )
        self.apply_result(envelope)

    def _log(self, event_type: str, **fields) -> None:
        if not self.structured_logger:
            return
        self.structured_logger.emit(event_type=event_type, **fields)
