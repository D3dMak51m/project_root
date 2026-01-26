from dataclasses import dataclass, replace
from typing import List
from enum import Enum


class StrategicMode(Enum):
    TACTICAL = "TACTICAL"
    BALANCED = "BALANCED"
    STRATEGIC = "STRATEGIC"


@dataclass(frozen=True)
class StrategicPosture:
    engagement_policy: List[str]

    # Long-term orientation parameters
    risk_tolerance: float = 0.5
    confidence_baseline: float = 0.5
    persistence_factor: float = 1.0

    # [NEW] Strategic Mode
    mode: StrategicMode = StrategicMode.BALANCED

    @property
    def horizon_days(self) -> int:
        """
        Derived horizon based on strategic mode.
        """
        if self.mode == StrategicMode.TACTICAL:
            return 2
        elif self.mode == StrategicMode.STRATEGIC:
            return 30
        return 7  # BALANCED

    def update(self, **changes) -> 'StrategicPosture':
        """
        Returns a new StrategicPosture with updated fields.
        Ensures immutability.
        """
        return replace(self, **changes)