from dataclasses import dataclass
from typing import List

@dataclass
class StrategicPosture:
    horizon_days: int
    engagement_policy: List[str]
    patience_level: float
    intervention_threshold: float