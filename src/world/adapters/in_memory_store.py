from typing import List, Optional
from datetime import datetime
from src.world.interfaces.signal_store import SignalStore
from src.world.domain.signal import NormalizedSignal


class InMemorySignalStore(SignalStore):
    """
    In-memory storage for signals.
    """

    def __init__(self):
        self._store: List[NormalizedSignal] = []

    def append(self, signal: NormalizedSignal) -> None:
        self._store.append(signal)

    def list(self, since: Optional[datetime] = None) -> List[NormalizedSignal]:
        if since is None:
            return list(self._store)

        return [s for s in self._store if s.received_at > since]