from typing import List, Dict
from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.ledger.strategic_event import StrategicEvent
from src.core.domain.strategic_context import StrategicContext

class InMemoryStrategicLedger(StrategicLedger):
    """
    Simple in-memory implementation.
    Uses string representation of StrategicContext as internal storage key,
    but interface operates strictly on StrategicContext objects.
    """
    def __init__(self):
        # Key: str(context), Value: List[StrategicEvent]
        self._store: Dict[str, List[StrategicEvent]] = {}

    def record(self, event: StrategicEvent) -> None:
        # Internal implementation detail: use str(context) as key
        key = str(event.context)
        if key not in self._store:
            self._store[key] = []
        self._store[key].append(event)

    def get_history(self, context: StrategicContext) -> List[StrategicEvent]:
        key = str(context)
        return list(self._store.get(key, []))