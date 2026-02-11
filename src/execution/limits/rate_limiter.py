from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Deque, Dict, Tuple


@dataclass(frozen=True)
class SlidingWindowLimit:
    max_events: int
    window_seconds: int


class InMemorySlidingRateLimiter:
    """
    Runtime-first rate limiter.
    Designed for hot-path checks without DB contention.
    """

    def __init__(
        self,
        global_limit: SlidingWindowLimit = SlidingWindowLimit(max_events=100, window_seconds=60),
        chat_limit: SlidingWindowLimit = SlidingWindowLimit(max_events=20, window_seconds=60),
    ):
        self.global_limit = global_limit
        self.chat_limit = chat_limit
        self._global_events: Deque[datetime] = deque()
        self._chat_events: Dict[str, Deque[datetime]] = {}
        self._lock = Lock()

    def allow(self, chat_key: str, now: datetime | None = None) -> Tuple[bool, float]:
        current = now or datetime.now(timezone.utc)
        with self._lock:
            self._trim(self._global_events, self.global_limit.window_seconds, current)
            chat_deque = self._chat_events.setdefault(chat_key, deque())
            self._trim(chat_deque, self.chat_limit.window_seconds, current)

            if len(self._global_events) >= self.global_limit.max_events:
                retry = self._retry_after(self._global_events, self.global_limit.window_seconds, current)
                return False, retry
            if len(chat_deque) >= self.chat_limit.max_events:
                retry = self._retry_after(chat_deque, self.chat_limit.window_seconds, current)
                return False, retry

            self._global_events.append(current)
            chat_deque.append(current)
            return True, 0.0

    def snapshot(self) -> Dict[str, int]:
        current = datetime.now(timezone.utc)
        with self._lock:
            self._trim(self._global_events, self.global_limit.window_seconds, current)
            out = {"global": len(self._global_events)}
            for key, values in self._chat_events.items():
                self._trim(values, self.chat_limit.window_seconds, current)
                out[f"chat:{key}"] = len(values)
            return out

    def _trim(self, data: Deque[datetime], window_seconds: int, now: datetime) -> None:
        cutoff = now - timedelta(seconds=window_seconds)
        while data and data[0] < cutoff:
            data.popleft()

    def _retry_after(self, data: Deque[datetime], window_seconds: int, now: datetime) -> float:
        if not data:
            return 0.0
        first = data[0]
        target = first + timedelta(seconds=window_seconds)
        return max(0.05, (target - now).total_seconds())
