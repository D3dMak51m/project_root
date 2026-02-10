from abc import ABC, abstractmethod
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory

class StrategicTrajectoryMemoryStore(ABC):
    """
    Interface for context-scoped strategic trajectory persistence.
    Decouples trajectory memory from the AIHuman entity.
    """

    @abstractmethod
    def load(self, context: StrategicContext) -> StrategicTrajectoryMemory:
        """
        Load trajectory memory for a specific strategic context.
        Should return an empty StrategicTrajectoryMemory if none exists.
        """
        pass

    @abstractmethod
    def save(
        self,
        context: StrategicContext,
        memory: StrategicTrajectoryMemory
    ) -> None:
        """
        Persist updated trajectory memory for a specific context.
        """
        pass