from dataclasses import dataclass
from typing import List, Optional
from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import SignalSalience, TrendWindow
from src.world.domain.target import TargetBinding
from src.interaction.domain.interaction_event import InteractionEvent


@dataclass(frozen=True)
class WorldObservation:
    """
    Aggregated view of a signal OR interaction with all its derived metrics and bindings.
    This is the raw material for cognitive processing.
    """
    # One of these must be present
    signal: Optional[NormalizedSignal] = None
    interaction: Optional[InteractionEvent] = None

    salience: Optional[SignalSalience] = None
    trends: List[TrendWindow] = None
    targets: Optional[TargetBinding] = None