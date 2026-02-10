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

        NOTE: The base MemoryStore does not expose a public method to clear or replace events.
        Directly accessing private fields (e.g., _events) violates architectural boundaries.
        Therefore, this implementation cannot be completed without extending the base MemoryStore contract.

        Per architectural constraints (M11 FIX), we must raise NotImplementedError rather than violate encapsulation.
        """
        raise NotImplementedError(
            "Atomic replacement requires explicit public contract on MemoryStore. "
            "Base MemoryStore does not support clear/replace operations."
        )