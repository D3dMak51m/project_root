from abc import ABC, abstractmethod
from src.world.domain.signal import NormalizedSignal
from src.world.domain.target import TargetBinding

class TargetResolver(ABC):
    """
    Interface for resolving targets and geography from a signal.
    Must be deterministic and rule-based.
    """
    @abstractmethod
    def resolve(self, signal: NormalizedSignal) -> TargetBinding:
        pass