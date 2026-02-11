from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import Lock
from typing import Dict, List, Optional


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitTransition:
    key: str
    previous: CircuitState
    current: CircuitState
    at: datetime
    reason: str


@dataclass
class _CircuitRuntimeState:
    state: CircuitState = CircuitState.CLOSED
    opened_at: Optional[datetime] = None
    failures: List[datetime] = None
    half_open_successes: int = 0
    probe_in_flight: bool = False

    def __post_init__(self):
        if self.failures is None:
            self.failures = []


class InMemoryCircuitBreaker:
    """
    Runtime-first breaker with persisted transition hooks.
    """

    def __init__(
        self,
        threshold: int = 5,
        window_seconds: int = 30,
        cooldown_seconds: int = 60,
        half_open_success_threshold: int = 2,
    ):
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.half_open_success_threshold = half_open_success_threshold
        self._state: Dict[str, _CircuitRuntimeState] = {}
        self._lock = Lock()
        self._transitions: List[CircuitTransition] = []

    def allow(self, key: str, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        with self._lock:
            state = self._state.setdefault(key, _CircuitRuntimeState())
            if state.state == CircuitState.CLOSED:
                return True
            if state.state == CircuitState.OPEN:
                if state.opened_at and (current - state.opened_at).total_seconds() >= self.cooldown_seconds:
                    self._transition(key, state, CircuitState.HALF_OPEN, current, "cooldown_elapsed")
                    state.probe_in_flight = False
                else:
                    return False
            if state.state == CircuitState.HALF_OPEN:
                if state.probe_in_flight:
                    return False
                state.probe_in_flight = True
                return True
            return True

    def record_success(self, key: str, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        with self._lock:
            state = self._state.setdefault(key, _CircuitRuntimeState())
            if state.state == CircuitState.CLOSED:
                state.failures.clear()
                return
            if state.state == CircuitState.HALF_OPEN:
                state.probe_in_flight = False
                state.half_open_successes += 1
                if state.half_open_successes >= self.half_open_success_threshold:
                    self._transition(key, state, CircuitState.CLOSED, current, "probe_success_threshold")
                    state.failures.clear()
                    state.half_open_successes = 0

    def record_failure(self, key: str, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        with self._lock:
            state = self._state.setdefault(key, _CircuitRuntimeState())
            if state.state == CircuitState.HALF_OPEN:
                state.probe_in_flight = False
                self._transition(key, state, CircuitState.OPEN, current, "half_open_probe_failure")
                state.opened_at = current
                state.half_open_successes = 0
                return

            cutoff = current - timedelta(seconds=self.window_seconds)
            state.failures = [x for x in state.failures if x >= cutoff]
            state.failures.append(current)
            if state.state == CircuitState.CLOSED and len(state.failures) >= self.threshold:
                self._transition(key, state, CircuitState.OPEN, current, "failure_threshold")
                state.opened_at = current

    def get_state(self, key: str) -> CircuitState:
        with self._lock:
            state = self._state.get(key)
            return state.state if state else CircuitState.CLOSED

    def drain_transitions(self) -> List[CircuitTransition]:
        with self._lock:
            out = list(self._transitions)
            self._transitions.clear()
            return out

    def _transition(
        self,
        key: str,
        state: _CircuitRuntimeState,
        target: CircuitState,
        now: datetime,
        reason: str,
    ) -> None:
        previous = state.state
        state.state = target
        self._transitions.append(
            CircuitTransition(
                key=key,
                previous=previous,
                current=target,
                at=now,
                reason=reason,
            )
        )
