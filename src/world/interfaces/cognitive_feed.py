from abc import ABC, abstractmethod
from typing import List
from src.world.domain.signal import NormalizedSignal
from src.world.domain.observation import WorldObservation

class CognitiveFeed(ABC):
    """
    Interface for building the cognitive feed from raw signals.
    Aggregates analysis results without interpretation.
    """
    @abstractmethod
    def build(self, signals: List[NormalizedSignal]) -> List[WorldObservation]:
        pass