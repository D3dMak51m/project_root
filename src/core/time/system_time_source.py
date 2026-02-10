from datetime import datetime, timezone
from src.core.time.time_source import TimeSource

class SystemTimeSource(TimeSource):
    """
    Production time source using system clock.
    Always returns UTC-aware datetime.
    """
    def now(self) -> datetime:
        return datetime.now(timezone.utc)