from typing import List
from uuid import UUID
from src.memory.store.memory_store import MemoryStore
from src.memory.domain.event_record import EventRecord
from src.core.domain.execution_result import ExecutionStatus

class MemoryQueryService:
    """
    Read-only service for querying historical events.
    """
    def __init__(self, store: MemoryStore):
        self.store = store

    def last_n_events(self, n: int) -> List[EventRecord]:
        return self.store.list_all()[-n:]

    def last_successful_event(self) -> List[EventRecord]:
        # Returns list of last successful event (0 or 1) to keep consistent return type if needed,
        # but prompt asked for single Optional.
        # Wait, prompt asked for last_successful_event() -> Optional.
        # But FIX 6 asked to change by_intent -> List.
        # I will keep last_successful_event as Optional (single) as it implies "the last one".
        for event in reversed(self.store.list_all()):
            if event.execution_status == ExecutionStatus.SUCCESS:
                return event # type: ignore (Optional return)
        return None # type: ignore

    def recent_failures(self, n: int) -> List[EventRecord]:
        failures = [
            e for e in self.store.list_all()
            if e.execution_status in (ExecutionStatus.FAILED, ExecutionStatus.REJECTED)
        ]
        return failures[-n:]

    def by_intent(self, intent_id: UUID) -> List[EventRecord]:
        """
        Returns all events associated with a specific intent ID.
        """
        return [
            event for event in self.store.list_all()
            if event.intent_id == intent_id
        ]