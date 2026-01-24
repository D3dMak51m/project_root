from dataclasses import dataclass, field
from typing import List, Optional, Dict

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
    stance_snapshot: Dict[str, float] = field(default_factory=dict)