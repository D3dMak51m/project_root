from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus
from src.autonomy.domain.autonomy_state import AutonomyState
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.domain.governance_snapshot import GovernanceSnapshot

@dataclass(frozen=True)
class EventRecord:
    """
    Immutable record of an executed (or attempted) action and its context.
    """
    id: UUID
    intent_id: UUID
    execution_status: ExecutionStatus
    execution_result: Optional[ExecutionResult]
    autonomy_state_before: AutonomyState
    # autonomy_state_after is not captured here as it evolves in next tick
    policy_decision: PolicyDecision
    governance_snapshot: GovernanceSnapshot
    issued_at: datetime