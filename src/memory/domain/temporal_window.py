from enum import Enum
from datetime import datetime, timedelta
from src.memory.domain.event_record import EventRecord


class TemporalWindow(Enum):
    IMMEDIATE = "IMMEDIATE"  # Very recent (e.g., last few ticks)
    RECENT = "RECENT"  # Short term (e.g., minutes)
    MID_TERM = "MID_TERM"  # Medium term (e.g., hours)
    LONG_TERM = "LONG_TERM"  # Long term (e.g., days)


def classify_window(event: EventRecord, now: datetime) -> TemporalWindow:
    """
    Pure function to classify an event into a temporal window.
    """
    age = (now - event.issued_at).total_seconds()

    # Thresholds (configurable in a real system, hardcoded for M.2 determinism)
    if age < 60:  # 1 minute
        return TemporalWindow.IMMEDIATE
    elif age < 3600:  # 1 hour
        return TemporalWindow.RECENT
    elif age < 86400:  # 24 hours
        return TemporalWindow.MID_TERM
    else:
        return TemporalWindow.LONG_TERM