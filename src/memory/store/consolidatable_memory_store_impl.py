from typing import List
from src.memory.store.memory_store import MemoryStore
from src.memory.interfaces.consolidatable_memory_store import ConsolidatableMemoryStore
from src.memory.domain.event_record import EventRecord


class ConsolidatableMemoryStoreImpl(MemoryStore, ConsolidatableMemoryStore):
    """
    Opt-in implementation of MemoryStore that supports atomic consolidation.
    Extends the base MemoryStore to add replace_all capability.
    """

    def list_all(self) -> List[EventRecord]:
        """
        Retrieve all events. Inherited behavior, explicit for interface compliance.
        """
        return super().list_all()

    def replace_all(self, events: List[EventRecord]) -> None:
        """
        Atomically replace the entire event history.
        """
        # Atomic assignment to the internal list
        self._events = list(events)