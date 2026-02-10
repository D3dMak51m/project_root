from typing import List
from datetime import datetime, timezone
from src.world.interfaces.signal_source import SignalSource
from src.world.domain.signal import RawSignal

class MockSignalSource(SignalSource):
    """
    Deterministic source for testing.
    Returns a predefined list of signals.
    """
    def __init__(self, signals: List[RawSignal]):
        self._signals = signals
        self._fetched = False

    def fetch(self) -> List[RawSignal]:
        if self._fetched:
            return []
        self._fetched = True
        return self._signals