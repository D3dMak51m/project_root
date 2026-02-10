from typing import List
from src.world.interfaces.signal_source import SignalSource
from src.world.interfaces.signal_normalizer import SignalNormalizer
from src.world.interfaces.signal_store import SignalStore
from src.world.domain.signal import NormalizedSignal

class SignalIngestionService:
    """
    Orchestrates the ingestion pipeline: Fetch -> Normalize -> Store.
    """
    def __init__(
        self,
        source: SignalSource,
        normalizer: SignalNormalizer,
        store: SignalStore
    ):
        self.source = source
        self.normalizer = normalizer
        self.store = store

    def ingest(self) -> List[NormalizedSignal]:
        """
        Executes the ingestion cycle.
        Returns the list of newly ingested signals.
        """
        raw_signals = self.source.fetch()
        ingested_signals = []

        for raw in raw_signals:
            normalized = self.normalizer.normalize(raw)
            self.store.append(normalized)
            ingested_signals.append(normalized)

        return ingested_signals