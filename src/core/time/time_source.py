from abc import ABC, abstractmethod
from datetime import datetime

class TimeSource(ABC):
    """
    Abstract source of time.
    Ensures all time in the system is UTC-aware and controllable.
    """
    @abstractmethod
    def now(self) -> datetime:
        pass