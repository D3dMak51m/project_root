from abc import ABC, abstractmethod
from datetime import timedelta

class MemoryDecayStrategy(ABC):
    """
    Interface for calculating the decay factor of a memory based on its age.
    Must be pure and deterministic.
    """
    @abstractmethod
    def decay(self, age: timedelta) -> float:
        """
        Returns a float between 0.0 (forgotten) and 1.0 (fresh).
        """
        pass