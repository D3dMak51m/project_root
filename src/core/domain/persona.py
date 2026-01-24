from dataclasses import dataclass
from typing import List
from uuid import UUID

@dataclass
class PersonaMask:
    id: UUID
    human_id: UUID
    platform: str
    display_name: str
    bio: str
    language: str
    tone: str
    verbosity: str
    activity_rate: float
    risk_tolerance: float
    posting_hours: List[int]