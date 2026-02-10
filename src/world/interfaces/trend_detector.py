from abc import ABC, abstractmethod
from typing import List
from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import TrendWindow

class TrendDetector(ABC):
    """
    Interface for detecting temporal patterns (trends).
    Must be pure and deterministic.
    """
    @abstractmethod
    def update(
        self,
        signal: NormalizedSignal,
        current_windows: List[TrendWindow]
    ) -> List[TrendWindow]:
        pass