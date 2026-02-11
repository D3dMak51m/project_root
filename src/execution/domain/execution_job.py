from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict
from uuid import UUID, uuid4

from src.core.domain.execution_intent import ExecutionIntent


class ExecutionJobState(Enum):
    QUEUED = "queued"
    LEASED = "leased"
    COMPLETED = "completed"
    DLQ = "dlq"


class DlqState(Enum):
    AWAITING_MANUAL_ACTION = "awaiting_manual_action"
    TERMINAL = "terminal"
    REPLAYED = "replayed"
    RESOLVED = "resolved"


@dataclass
class ExecutionJob:
    id: UUID
    intent: ExecutionIntent
    context_domain: str
    reservation_delta: Dict[str, float]
    state: ExecutionJobState = ExecutionJobState.QUEUED
    priority: float = 0.0
    available_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    leased_by: Optional[str] = None
    lease_until: Optional[datetime] = None
    attempt_count: int = 0
    max_attempts: int = 5
    last_error: Optional[str] = None
    job_version: int = 1
    parent_job_id: Optional[UUID] = None
    dlq_state: Optional[DlqState] = None

    @classmethod
    def new(
        cls,
        intent: ExecutionIntent,
        context_domain: str,
        reservation_delta: Dict[str, float],
        priority: float = 0.0,
        max_attempts: int = 5,
    ) -> "ExecutionJob":
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            intent=intent,
            context_domain=context_domain,
            reservation_delta=reservation_delta,
            priority=priority,
            available_at=now,
            created_at=now,
            updated_at=now,
            max_attempts=max_attempts,
        )
