from dataclasses import dataclass, field
from typing import List
from uuid import UUID, uuid4

@dataclass
class PersonaMask:
    id: UUID
    human_id: UUID

    platform: str                  # telegram | twitter | youtube
    display_name: str
    bio: str

    language: str
    tone: str                      # calm | aggressive | ironic | neutral
    verbosity: str                 # short | medium | long

    activity_rate: float           # 0.0–1.0 (how often allowed to act)
    risk_tolerance: float          # 0.0–1.0 (how risky content can be)

    posting_hours: List[int]       # allowed hours (local time)

    @classmethod
    def create(cls, human_id: UUID, platform: str, display_name: str) -> "PersonaMask":
        return cls(
            id=uuid4(),
            human_id=human_id,
            platform=platform,
            display_name=display_name,
            bio="",
            language="ru",
            tone="neutral",
            verbosity="medium",
            activity_rate=0.2,
            risk_tolerance=0.3,
            posting_hours=list(range(9, 23))
        )