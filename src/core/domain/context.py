from dataclasses import dataclass, field
from typing import List, Optional
from typing import List
from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState


@dataclass
class PerceivedWorldSummary:
    """
    Subjective, lossy, fuzzy snapshot of the world.
    """
    dominant_mood: str  # e.g., "Tense", "Boring", "Chaotic"
    interesting_topics: List[str]
    uncertainty_level: float  # 0.0 to 1.0
    last_perceived_at: str  # ISO timestamp


@dataclass
class InternalContext:
    """
    L3 Context: Subjective worldview.
    Constructed ONLY from internal state, identity, and memory.
    No external inputs yet.
    """
    identity_summary: str
    current_mood: str  # Derived from traits + state
    energy_level: str  # Qualitative description
    recent_thoughts: List[str]
    active_intentions_count: int

    world_perception: Optional[PerceivedWorldSummary] = None

    @classmethod
    def build(
            cls,
            identity: Identity,
            state: BehaviorState,
            memories: List[str],
            intentions_count: int,
            world_perception: Optional[PerceivedWorldSummary] = None
    ) -> 'InternalContext':

        # Simple logic to map quantitative state to qualitative description
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
            world_perception=world_perception
        )

    def to_prompt_string(self) -> str:
        base = (
            f"IDENTITY: {self.identity_summary}\n"
            f"STATE: Energy is {self.energy_level}.\n"
            f"RECENT THOUGHTS: {'; '.join(self.recent_thoughts)}\n"
            f"PENDING PLANS: {self.active_intentions_count}\n"
        )

        if self.world_perception:
            world = (
                f"WORLD SENSE: The world feels {self.world_perception.dominant_mood}. "
                f"I noticed: {', '.join(self.world_perception.interesting_topics)}. "
                f"Uncertainty: {self.world_perception.uncertainty_level:.1f}"
            )
            return base + world

        return base + "WORLD SENSE: I haven't looked outside recently."