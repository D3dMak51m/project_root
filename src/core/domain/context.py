from dataclasses import dataclass
from typing import List
from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState


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

    @classmethod
    def build(cls, identity: Identity, state: BehaviorState, memories: List[str], intentions_count: int) -> 'InternalContext':
        # Simple logic to map quantitative state to qualitative description
        energy_desc = "High"
        if state.energy < 30:
            energy_desc = "Exhausted"
        elif state.energy < 70:
            energy_desc = "Moderate"

        return cls(
            identity_summary=identity.summary(),
            current_mood="Neutral",  # Placeholder for complex mood logic
            energy_level=energy_desc,
            recent_thoughts=memories,
            active_intentions_count=intentions_count
        )

    def to_prompt_string(self) -> str:
        return (
            f"IDENTITY: {self.identity_summary}\n"
            f"STATE: Energy is {self.energy_level}.\n"
            f"RECENT THOUGHTS: {'; '.join(self.recent_thoughts)}\n"
            f"PENDING PLANS: {self.active_intentions_count}"
        )