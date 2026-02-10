from abc import ABC, abstractmethod
from uuid import UUID

class MemoryIdSource(ABC):
    """
    Abstract source of IDs for memory events.
    Ensures determinism and replayability.
    """
    @abstractmethod
    def new_id(self) -> UUID:
        pass

class SystemMemoryIdSource(MemoryIdSource):
    def new_id(self) -> UUID:
        from uuid import uuid4
        return uuid4()