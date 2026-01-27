from typing import List
from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.ledger.strategic_event import StrategicEvent

class InMemoryStrategicLedger(StrategicLedger):
    """
    Simple in-memory implementation for C.18.1/E.1.
    """
    def __init__(self):
        self._events: List[StrategicEvent] = []

    def record(self, event: StrategicEvent) -> None:
        self._events.append(event)

    def get_history(self) -> List[StrategicEvent]:
        return list(self._events)