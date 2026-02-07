from dataclasses import dataclass, field
from typing import Dict
from src.interaction.domain.envelope import PriorityHint

@dataclass(frozen=True)
class SilenceProfile:
    """
    Configuration for silence governance.
    Defines thresholds for pressure required to break silence.
    """
    base_pressure_threshold: float
    priority_overrides: Dict[PriorityHint, float] = field(default_factory=dict)
    cooldown_required: bool = False