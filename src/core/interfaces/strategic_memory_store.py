from abc import ABC, abstractmethod
from typing import Optional
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategic_memory import StrategicMemory

class StrategicMemoryStore(ABC):
    """
    Interface for retrieving and persisting strategic memory.
    Decouples memory from the AIHuman entity.
    """

    @abstractmethod
    def load(self, context: StrategicContext) -> StrategicMemory:
        """
        Load memory for a specific strategic context.
        Should return an empty StrategicMemory if none exists.
        """
        pass

    @abstractmethod
    def save(self, context: StrategicContext, memory: StrategicMemory) -> None:
        """
        Persist updated memory for a specific context.
        """
        pass