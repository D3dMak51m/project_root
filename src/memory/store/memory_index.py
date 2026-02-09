from typing import Dict, List
from uuid import UUID
from src.memory.store.memory_store import MemoryStore
from src.memory.domain.event_record import EventRecord

class MemoryIndex:
    """
    Pure helper to build indices over MemoryStore.
    Does NOT mutate events.
    """
    def __init__(self, store: MemoryStore):
        self.store = store

    def build_intent_index(self) -> Dict[UUID, List[EventRecord]]:
        index: Dict[UUID, List[EventRecord]] = {}
        for event in self.store.list_all():
            if event.intent_id not in index:
                index[event.intent_id] = []
            index[event.intent_id].append(event)
        return index

    def build_status_index(self) -> Dict[str, List[EventRecord]]:
        index: Dict[str, List[EventRecord]] = {}
        for event in self.store.list_all():
            status = event.execution_status.value
            if status not in index:
                index[status] = []
            index[status].append(event)
        return index