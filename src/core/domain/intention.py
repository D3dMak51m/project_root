from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Dict, Any

@dataclass
class Intention:
    id: UUID
    type: str
    content: str
    priority: int
    created_at: datetime
    ttl_seconds: int
    metadata: Dict[str, Any]

@dataclass
class DeferredAction:
    id: UUID
    intention_id: UUID
    reason: str
    resume_after: datetime