from datetime import datetime, timedelta, timezone
from src.core.time.time_source import TimeSource

class FrozenTimeSource(TimeSource):
    """
    Test time source.
    Allows deterministic time progression.
    """
    def __init__(self, start_time: datetime):
        if start_time.tzinfo is None:
            raise ValueError("FrozenTimeSource requires timezone-aware datetime")
        self._current_time = start_time

    def now(self) -> datetime:
        return self._current_time

    def advance(self, delta: timedelta):
        self._current_time += delta