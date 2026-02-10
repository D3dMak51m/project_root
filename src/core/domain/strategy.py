from dataclasses import dataclass, replace
from typing import List, Any, Dict
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

    # Strategic Mode
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategicPosture':
        return cls(
            engagement_policy=data['engagement_policy'],
            risk_tolerance=data['risk_tolerance'],
            confidence_baseline=data['confidence_baseline'],
            persistence_factor=data['persistence_factor'],
            mode=StrategicMode(data['mode'])
        )