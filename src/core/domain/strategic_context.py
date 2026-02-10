from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class StrategicContext:
    """
    Defines the scope for strategic memory and adaptation.
    Strategy is not global to the agent, but specific to a context.
    """
    country: str
    region: Optional[str]
    goal_id: Optional[str]
    domain: str  # e.g., "social_media", "finance", "research"

    def __str__(self) -> str:
        return f"{self.country}/{self.region or '*'}/{self.domain}/{self.goal_id or '*'}"