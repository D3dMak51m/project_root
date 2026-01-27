from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional

@dataclass
class ActionProposal:
    id: UUID
    intention_id: UUID
    type: str
    content: str
    risk_level: float
    energy_cost: float
    created_at: datetime

    @classmethod
    def create(cls, intention_id: UUID, type: str, content: str, now: datetime, risk: float = 0.1) -> 'ActionProposal':
        return cls(
            id=uuid4(),
            intention_id=intention_id,
            type=type,
            content=content,
            risk_level=risk,
            energy_cost=10.0 + (risk * 10.0),
            created_at=now
        )
