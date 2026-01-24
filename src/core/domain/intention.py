from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Optional, Dict, Any

@dataclass
class Intention:
    id: UUID
    type: str  # e.g., "post_telegram", "rest", "research"
    content: str  # Internal description of what to do
    priority: int  # 1-10
    created_at: datetime
    ttl_seconds: int
    metadata: Dict[str, Any]

    @property
    def expires_at(self) -> datetime:
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    def is_expired(self, current_time: datetime) -> bool:
        return current_time > self.expires_at

    @classmethod
    def create(cls, type: str, content: str, priority: int = 5, ttl: int = 3600) -> 'Intention':
        return cls(
            id=uuid4(),
            type=type,
            content=content,
            priority=priority,
            created_at=datetime.utcnow(),
            ttl_seconds=ttl,
            metadata={}
        )