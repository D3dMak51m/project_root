from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from src.interaction.domain.envelope import InteractionEnvelope

@dataclass(frozen=True)
class ExecutionCommand:
    """
    Immutable command representing a fully authorized autonomous action.
    This is the final artifact before the ExecutionDispatcher.
    """
    id: UUID
    envelope: InteractionEnvelope
    issued_at: datetime