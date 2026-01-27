from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Dict, Any

@dataclass
class Intention:
    id: UUID
    type: str
    content: str
    priority: float
    created_at: datetime
    ttl_seconds: int
    metadata: Dict[str, Any]

    def is_expired(self, now: datetime) -> bool:
        age_seconds = (now - self.created_at).total_seconds()
        return age_seconds > self.ttl_seconds

@dataclass
class DeferredAction:
    id: UUID
    intention_id: UUID
    reason: str
    resume_after: datetime