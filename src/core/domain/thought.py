from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass(frozen=True)
class ThoughtArtifact:
    """
    READ-ONLY result of thinking.
    Has no authority over the system.
    """
    summary: str
    internal_monologue: str
    salient_points: List[str]
    emotional_tone: str
    created_at: datetime