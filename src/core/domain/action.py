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
    platform: str
    risk_level: float
    energy_cost: float
    created_at: datetime

    @classmethod
    def create(cls, intention_id: UUID, type: str, content: str, risk: float = 0.1) -> 'ActionProposal':
        return cls(
            id=uuid4(),
            intention_id=intention_id,
            type=type,
            content=content,
            platform="abstract",
            risk_level=risk,
            energy_cost=10.0 + (risk * 10.0),
            created_at=datetime.utcnow()
        )


@dataclass
class ExecutionResult:
    success: bool
    action_taken: Optional[ActionProposal] = None
    energy_cost: float = 0.0
    readiness_decay: float = 0.0
    executed_intention_id: Optional[UUID] = None
    memory_content: Optional[str] = None