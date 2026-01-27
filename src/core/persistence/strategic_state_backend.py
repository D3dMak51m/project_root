from abc import ABC, abstractmethod
from typing import Optional

from src.core.domain.strategic_context import StrategicContext
from src.core.persistence.strategic_state_bundle import StrategicStateBundle

class StrategicStateBackend(ABC):
    """
    Interface for persisting and retrieving strategic state.
    Decouples the core logic from storage implementation details.
    """

    @abstractmethod
    def load(self, context: StrategicContext) -> Optional[StrategicStateBundle]:
        """
        Load the strategic state for a given context.
        Returns None if no state exists (cold start).
        """
        pass

    @abstractmethod
    def save(self, context: StrategicContext, bundle: StrategicStateBundle) -> None:
        """
        Persist the strategic state for a given context.
        """
        pass