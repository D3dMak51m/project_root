from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class ExecutionWindow:
    """
    Transient object representing a momentary opportunity to act.
    Does NOT guarantee execution.
    Exists only within a single LifeLoop tick.
    """
    intention_id: UUID
    persona_id: UUID
    opened_at: datetime
    expires_at: datetime
    confidence: float  # 0.0 - 1.0
    reason: str