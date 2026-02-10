from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class SignalSalience:
    """
    Quantitative visibility metrics for a signal.
    Purely mathematical, no semantic interpretation.
    """
    signal_id: UUID
    source_id: str
    timestamp: datetime

    frequency_score: float     # 0.0 - 1.0 (normalized repetition rate)
    novelty_score: float       # 0.0 - 1.0 (uniqueness vs history)
    volume_score: float        # 0.0 - 1.0 (burst intensity)

    salience_score: float      # 0.0 - 1.0 (aggregated visibility)

@dataclass(frozen=True)
class TrendWindow:
    """
    Time-windowed aggregation of signal occurrences.
    Used to detect growth or decay.
    """
    key: str                  # Content hash or fingerprint
    window_start: datetime
    window_end: datetime

    count: int
    delta: float              # Rate of change (velocity)