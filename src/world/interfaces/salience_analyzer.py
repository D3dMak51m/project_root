from abc import ABC, abstractmethod
from typing import List
from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import SignalSalience

class SalienceAnalyzer(ABC):
    """
    Interface for calculating visibility metrics.
    Must be pure and deterministic.
    """
    @abstractmethod
    def evaluate(
        self,
        signal: NormalizedSignal,
        history: List[NormalizedSignal]
    ) -> SignalSalience:
        pass