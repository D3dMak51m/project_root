from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional
from src.core.domain.execution_intent import ExecutionIntent
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.domain.governance_snapshot import GovernanceSnapshot

@dataclass(frozen=True)
class CounterfactualEvent:
    """
    Immutable record of an intention that was NOT executed.
    Captures the "what could have been" and "why it wasn't".
    """
    id: UUID
    intent_id: UUID
    intent: Optional[ExecutionIntent] # May be None if suppressed before binding
    reason: str # e.g., "Policy Block", "Budget Rejection", "Governance Lock"
    suppression_stage: str # "Policy", "Governance", "Budget", "Arbitration"
    policy_decision: Optional[PolicyDecision]
    governance_snapshot: GovernanceSnapshot
    context_domain: str
    timestamp: datetime