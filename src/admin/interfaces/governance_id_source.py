from abc import ABC, abstractmethod
from uuid import UUID

class GovernanceIdSource(ABC):
    """
    Abstract source of IDs for governance entities.
    Ensures determinism and replayability.
    """
    @abstractmethod
    def new_id(self) -> UUID:
        pass