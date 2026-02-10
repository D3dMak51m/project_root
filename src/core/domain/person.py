from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import List

@dataclass
class PersonProfile:
    id: UUID
    external_ids: List[str]
    attitude: float
    trust: float
    tension: float
    role: str
    interaction_count: int
    last_interaction: datetime