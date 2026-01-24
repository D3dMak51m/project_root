from dataclasses import dataclass
from typing import List, Optional
from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState
from src.core.domain.readiness import ActionReadiness


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
    world_perception: Optional[PerceivedWorldSummary] = None

    # [NEW] Structured Readiness Data
    readiness_level: str = "passive"
    readiness_value: float = 0.0

    @classmethod
    def build(
            cls,
            identity: Identity,
            state: BehaviorState,
            memories: List[str],
            intentions_count: int,
            readiness: ActionReadiness,  # [NEW]
            world_perception: Optional[PerceivedWorldSummary] = None
    ) -> 'InternalContext':

        energy_desc = "High"
        if state.energy < 30:
            energy_desc = "Exhausted"
        elif state.energy < 70:
            energy_desc = "Moderate"

        return cls(
            identity_summary=identity.summary(),
            current_mood="Neutral",
            energy_level=energy_desc,
            recent_thoughts=memories,
            active_intentions_count=intentions_count,
            world_perception=world_perception,
            readiness_level=readiness.level.value,
            readiness_value=readiness.value
        )

    def to_prompt_string(self) -> str:
        base = (
            f"IDENTITY: {self.identity_summary}\n"
            f"STATE: Energy is {self.energy_level}. "
            f"Action Readiness: {self.readiness_level} ({self.readiness_value:.1f}/100).\n"  # [NEW]
            f"RECENT THOUGHTS: {'; '.join(self.recent_thoughts)}\n"
            f"PENDING PLANS: {self.active_intentions_count}\n"
        )

        if self.world_perception:
            world = (
                f"WORLD SENSE: The world feels {self.world_perception.dominant_mood}. "
                f"I noticed: {', '.join(self.world_perception.interesting_topics)}. "
            )
            return base + world

        return base + "WORLD SENSE: I haven't looked outside recently."