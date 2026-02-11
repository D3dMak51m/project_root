from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, pstdev
from threading import Lock
from typing import Callable, Deque, Dict, Optional

from src.core.domain.execution_result import ExecutionResult, ExecutionStatus
from src.interaction.domain.interaction_event import InteractionEvent


class AnomalyHook(ABC):
    @abstractmethod
    def on_inbound(self, event: InteractionEvent) -> None:
        pass

    @abstractmethod
    def on_outbound(self, result: ExecutionResult, context_domain: Optional[str] = None) -> None:
        pass


class NoopAnomalyHook(AnomalyHook):
    def on_inbound(self, event: InteractionEvent) -> None:
        return

    def on_outbound(self, result: ExecutionResult, context_domain: Optional[str] = None) -> None:
        return


@dataclass(frozen=True)
class AnomalyEvent:
    event_type: str
    at: datetime
    context_domain: Optional[str]
    value: float
    baseline_mean: float
    baseline_std: float


class StatisticalAnomalyHook(AnomalyHook):
    """
    Telemetry-only heuristic anomaly detector.
    """

    def __init__(
        self,
        history_size: int = 50,
        z_threshold: float = 3.0,
        callback: Optional[Callable[[AnomalyEvent], None]] = None,
    ):
        self.history_size = max(10, int(history_size))
        self.z_threshold = float(z_threshold)
        self.callback = callback
        self._outbound: Dict[str, Deque[float]] = {}
        self._inbound: Dict[str, Deque[float]] = {}
        self._lock = Lock()

    def on_inbound(self, event: InteractionEvent) -> None:
        key = f"{event.platform}:{event.chat_id}"
        size = float(len(event.content or ""))
        self._observe(self._inbound, key, size, "INBOUND_CONTENT_ANOMALY")

    def on_outbound(self, result: ExecutionResult, context_domain: Optional[str] = None) -> None:
        key = context_domain or "global"
        value = 1.0 if result.status != ExecutionStatus.SUCCESS else 0.0
        self._observe(self._outbound, key, value, "OUTBOUND_FAILURE_DENSITY_ANOMALY")

    def _observe(
        self,
        store: Dict[str, Deque[float]],
        key: str,
        value: float,
        event_type: str,
    ) -> None:
        with self._lock:
            history = store.setdefault(key, deque(maxlen=self.history_size))
            if len(history) >= 10:
                values = list(history)
                avg = mean(values)
                std = pstdev(values)
                if std > 0:
                    z = abs((value - avg) / std)
                    if z >= self.z_threshold and self.callback:
                        self.callback(
                            AnomalyEvent(
                                event_type=event_type,
                                at=datetime.now(timezone.utc),
                                context_domain=key,
                                value=value,
                                baseline_mean=avg,
                                baseline_std=std,
                            )
                        )
            history.append(value)

