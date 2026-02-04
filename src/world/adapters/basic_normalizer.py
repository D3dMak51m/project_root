from uuid import uuid4
from datetime import datetime
from src.world.interfaces.signal_normalizer import SignalNormalizer
from src.world.domain.signal import RawSignal, NormalizedSignal

class BasicSignalNormalizer(SignalNormalizer):
    """
    Simple normalizer that converts payload to string and generates IDs.
    Assumes payload is convertible to string.
    """
    def normalize(self, raw: RawSignal) -> NormalizedSignal:
        return NormalizedSignal(
            signal_id=uuid4(),
            source_id=raw.source_id,
            received_at=raw.received_at,
            observed_at=raw.received_at, # Default to received time
            content=str(raw.payload),
            metadata={}
        )