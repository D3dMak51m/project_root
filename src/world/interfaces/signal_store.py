from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from src.world.domain.signal import NormalizedSignal

class SignalStore(ABC):
    """
    Interface for persisting normalized signals.
    """
    @abstractmethod
    def append(self, signal: NormalizedSignal) -> None:
        pass

    @abstractmethod
    def list(self, since: Optional[datetime] = None) -> List[NormalizedSignal]:
        pass