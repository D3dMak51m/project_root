from dataclasses import dataclass
from uuid import UUID
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

@dataclass
class ExecutionResult:
    success: bool
    action_taken: Optional[ActionProposal]
    energy_cost: float
    readiness_decay: float
    executed_intention_id: Optional[UUID]
    memory_content: Optional[str]