from abc import ABC, abstractmethod
from typing import Any, Dict


class WorldAdapter(ABC):
    """
    Abstract interface for interacting with the external environment.
    Isolates the Actor from specific API implementations.
    """

    @abstractmethod
    def perform(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a low-level operation in the world.
        Returns raw result data.
        """
        pass

    @abstractmethod
    def check_status(self) -> bool:
        """
        Check if the external system is available.
        """
        pass