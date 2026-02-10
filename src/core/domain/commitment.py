from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass(frozen=True)
class ExecutionCommitment:
    """
    Irreversible intent to act.
    Represents the crossing of the Rubicon from 'opportunity' to 'decision'.
    Contains all semantic decisions made prior to binding.
    """
    id: UUID
    intention_id: UUID
    persona_id: UUID
    origin_window_id: UUID
    committed_at: datetime
    confidence: float

    # [NEW] Semantic decisions fixed at commitment time
    abstract_action: str
    risk_level: float