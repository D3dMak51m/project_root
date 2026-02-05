from dataclasses import dataclass, field
from typing import List
from src.autonomy.domain.autonomy_mode import AutonomyMode

@dataclass(frozen=True)
class AutonomyState:
    """
    Immutable state representing the system's readiness to act autonomously.
    Pure data, no behavior.
    """
    mode: AutonomyMode
    justification: str
    pressure_level: float  # 0.0 - 1.0
    constraints: List[str] = field(default_factory=list)
    requires_human: bool = False