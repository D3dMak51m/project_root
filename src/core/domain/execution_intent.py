from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class ExecutionIntent:
    """
    Projection of an ExecutionCommitment into an actionable plan.
    Represents the boundary object passed to the external world.
    Does NOT contain execution logic or payload.
    """
    id: UUID
    commitment_id: UUID
    intention_id: UUID
    persona_id: UUID
    abstract_action: str  # e.g., "communicate", "observe", "interact"
    constraints: Dict[str, Any]
    created_at: datetime
    reversible: bool
    risk_level: float