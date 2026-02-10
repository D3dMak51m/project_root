from src.memory.store.memory_store import MemoryStore
from src.memory.domain.event_record import EventRecord

class MemoryIngestionService:
    """
    Service responsible for persisting EventRecords into the store.
    """
    def __init__(self, store: MemoryStore):
        self.store = store

    def ingest(self, event: EventRecord) -> None:
        self.store.append(event)