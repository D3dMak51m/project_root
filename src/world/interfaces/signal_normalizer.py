from abc import ABC, abstractmethod
from src.world.domain.signal import RawSignal, NormalizedSignal

class SignalNormalizer(ABC):
    """
    Interface for converting raw signals into canonical form.
    Strictly formatting and cleaning, NO semantic interpretation.
    """
    @abstractmethod
    def normalize(self, raw: RawSignal) -> NormalizedSignal:
        """
        Converts raw signal into canonical form.
        """
        pass