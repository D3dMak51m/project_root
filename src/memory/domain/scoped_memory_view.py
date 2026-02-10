from dataclasses import dataclass
from typing import List
from src.memory.domain.event_record import EventRecord

@dataclass(frozen=True)
class ScopedMemoryView:
    """
    A filtered view of the memory store, containing only events relevant
    to a specific strategic context or scope.
    """
    events: List[EventRecord]