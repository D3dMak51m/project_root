from typing import List
from src.memory.domain.event_record import EventRecord

class MemoryStore:
    """
    Append-only in-memory storage for EventRecords.
    """
    def __init__(self):
        self._events: List[EventRecord] = []

    def append(self, event: EventRecord) -> None:
        self._events.append(event)

    def list_all(self) -> List[EventRecord]:
        return list(self._events)