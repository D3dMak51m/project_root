from dataclasses import dataclass
from typing import List
from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import SignalSalience, TrendWindow
from src.world.domain.target import TargetBinding

@dataclass(frozen=True)
class WorldObservation:
    """
    Aggregated view of a signal with all its derived metrics and bindings.
    This is the raw material for cognitive processing.
    """
    signal: NormalizedSignal
    salience: SignalSalience
    trends: List[TrendWindow]
    targets: TargetBinding