from abc import ABC, abstractmethod
from typing import List
from src.core.ledger.strategic_event import StrategicEvent

class StrategicLedger(ABC):
    """
    Append-only log of strategic events.
    """
    @abstractmethod
    def record(self, event: StrategicEvent) -> None:
        pass

    @abstractmethod
    def get_history(self) -> List[StrategicEvent]:
        pass