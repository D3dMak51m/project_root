from abc import ABC, abstractmethod
from datetime import datetime

class GovernanceTimeSource(ABC):
    """
    Abstract source of time for governance operations.
    Ensures determinism and replayability.
    """
    @abstractmethod
    def now(self) -> datetime:
        pass