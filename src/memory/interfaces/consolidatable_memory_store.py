from typing import List, Protocol
from src.memory.domain.event_record import EventRecord

class ConsolidatableMemoryStore(Protocol):
    """
    Contract for memory stores that support atomic consolidation (replacement).
    """
    def list_all(self) -> List[EventRecord]:
        """Retrieve all events for consolidation analysis."""
        ...

    def replace_all(self, events: List[EventRecord]) -> None:
        """Atomically replace the entire event history with a consolidated set."""
        ...