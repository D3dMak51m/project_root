from abc import ABC, abstractmethod
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategy import StrategicPosture
from src.core.ledger.strategic_event import StrategicEvent


class SnapshotPolicy(ABC):
    @abstractmethod
    def should_save(
            self,
            context: StrategicContext,
            tick_count: int,
            last_event: StrategicEvent,
            current_posture: StrategicPosture
    ) -> bool:
        pass


class DefaultSnapshotPolicy(SnapshotPolicy):
    def __init__(self, interval_ticks: int = 100):
        self.interval_ticks = interval_ticks

    def should_save(
            self,
            context: StrategicContext,
            tick_count: int,
            last_event: StrategicEvent,
            current_posture: StrategicPosture
    ) -> bool:
        # Save on significant strategic shifts
        if last_event and last_event.event_type in ("MODE_SHIFT", "REBINDING"):
            return True

        # Save periodically
        if tick_count % self.interval_ticks == 0:
            return True

        return False