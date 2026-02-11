from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from typing import Dict

from src.core.domain.execution_result import ExecutionResult


@dataclass(frozen=True)
class ExecutionResultEnvelope:
    job_id: UUID
    intent_id: UUID
    context_domain: str
    reservation_delta: Dict[str, float]
    result: ExecutionResult
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
