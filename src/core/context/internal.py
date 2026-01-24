from dataclasses import dataclass, field
from typing import List, Optional, Dict
from uuid import UUID
from src.core.domain.execution import ExecutionEligibilityResult
from src.core.domain.window import ExecutionWindow


@dataclass
class PerceivedWorldSummary:
    dominant_mood: str
    interesting_topics: List[str]
    uncertainty_level: float
    last_perceived_at: str


@dataclass
class InternalContext:
    identity_summary: str
    current_mood: str
    energy_level: str
    recent_thoughts: List[str]
    active_intentions_count: int
    readiness_level: str
    readiness_value: float
    world_perception: Optional[PerceivedWorldSummary]

    # Read-only snapshot of stance intensities
    stance_snapshot: Dict[str, float] = field(default_factory=dict)

    # Read-only map of intention eligibility
    execution_eligibility: Dict[UUID, ExecutionEligibilityResult] = field(default_factory=dict)

    # [NEW] Transient execution window (if any)
    # ThinkingEngine can observe this but cannot create or modify it.
    execution_window: Optional[ExecutionWindow] = None