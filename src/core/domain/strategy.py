from dataclasses import dataclass, replace
from typing import List


@dataclass(frozen=True)
class StrategicPosture:
    horizon_days: int
    engagement_policy: List[str]

    # [UPDATED] Long-term orientation parameters
    # Removed: patience_level, intervention_threshold (moved to Volition/Physics)

    risk_tolerance: float = 0.5
    confidence_baseline: float = 0.5
    persistence_factor: float = 1.0

    def update(self, **changes) -> 'StrategicPosture':
        """
        Returns a new StrategicPosture with updated fields.
        Ensures immutability.
        """
        return replace(self, **changes)