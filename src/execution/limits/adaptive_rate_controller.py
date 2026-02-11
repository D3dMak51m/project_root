from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Dict

from src.core.domain.execution_result import ExecutionFailureType, ExecutionResult, ExecutionStatus


@dataclass
class _AdaptiveRuntimeState:
    delay_seconds: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AdaptiveRateController:
    """
    AIMD-style adaptive throttle for outbound hot-path.
    """

    def __init__(
        self,
        max_delay_seconds: float = 10.0,
        increase_step_seconds: float = 0.5,
        decrease_step_seconds: float = 0.25,
        queue_lag_weight: float = 0.02,
    ):
        self.max_delay_seconds = max(0.1, float(max_delay_seconds))
        self.increase_step_seconds = max(0.01, float(increase_step_seconds))
        self.decrease_step_seconds = max(0.01, float(decrease_step_seconds))
        self.queue_lag_weight = max(0.0, float(queue_lag_weight))
        self._state: Dict[str, _AdaptiveRuntimeState] = {}
        self._lock = Lock()

    def pre_send_delay(self, platform: str, queue_lag: float = 0.0) -> float:
        with self._lock:
            state = self._state.setdefault(platform, _AdaptiveRuntimeState())
            lag_penalty = max(0.0, float(queue_lag)) * self.queue_lag_weight
            return min(self.max_delay_seconds, state.delay_seconds + lag_penalty)

    def record_result(self, platform: str, result: ExecutionResult) -> None:
        with self._lock:
            state = self._state.setdefault(platform, _AdaptiveRuntimeState())
            if self._is_pressure_failure(result):
                state.delay_seconds = min(
                    self.max_delay_seconds,
                    (state.delay_seconds * 0.5) + self.increase_step_seconds,
                )
            elif result.status == ExecutionStatus.SUCCESS:
                state.delay_seconds = max(0.0, state.delay_seconds - self.decrease_step_seconds)
            state.last_updated = datetime.now(timezone.utc)

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            return {platform: state.delay_seconds for platform, state in self._state.items()}

    def _is_pressure_failure(self, result: ExecutionResult) -> bool:
        if result.failure_type != ExecutionFailureType.ENVIRONMENT:
            return False
        reason = (result.reason or "").lower()
        return "429" in reason or "rate" in reason or "5xx" in reason
