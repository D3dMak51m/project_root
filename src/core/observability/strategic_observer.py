from abc import ABC, abstractmethod
from src.core.ledger.strategic_event import StrategicEvent

class StrategicObserver(ABC):
    """
    Hook interface for observing strategic events.
    Implementations must not have side effects on the core logic.
    """
    @abstractmethod
    def on_event(self, event: StrategicEvent) -> None:
        pass