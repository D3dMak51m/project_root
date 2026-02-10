from abc import ABC, abstractmethod
from typing import List
from src.core.ledger.strategic_event import StrategicEvent
from src.core.domain.strategic_context import StrategicContext

class StrategicLedger(ABC):
    """
    Append-only log of strategic events.
    Context-aware: stores and retrieves events scoped by StrategicContext.
    """
    @abstractmethod
    def record(self, event: StrategicEvent) -> None:
        pass

    @abstractmethod
    def get_history(self, context: StrategicContext) -> List[StrategicEvent]:
        """
        Retrieve events strictly belonging to the given context.
        """
        pass