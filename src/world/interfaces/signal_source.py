from abc import ABC, abstractmethod
from typing import List
from src.world.domain.signal import RawSignal

class SignalSource(ABC):
    """
    Interface for fetching raw signals from the external world.
    Implementations handle connection logic (API, File, RSS).
    """
    @abstractmethod
    def fetch(self) -> List[RawSignal]:
        """
        Fetches new raw signals from the source.
        Must be side-effect free regarding the core system state.
        """
        pass