from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class StrategicSignals:
    """
    Semantic interpretation of execution outcomes.
    Used ONLY by strategy and planning layers.
    Does NOT affect physics (readiness, energy, etc.).
    """
    outcome_classification: str        # "success", "blocked", "unstable", "hostile_env"
    confidence_delta: float             # -1.0 .. +1.0
    risk_reassessment: float            # -1.0 .. +1.0
    persistence_bias: float             # 0.0 .. 2.0
    notes: List[str] = field(default_factory=list)