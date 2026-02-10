from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from src.interaction.domain.envelope import InteractionEnvelope
from src.autonomy.domain.autonomy_state import AutonomyState
from src.interaction.domain.policy_decision import PolicyDecision

@dataclass(frozen=True)
class HumanOverrideRequest:
    """
    Immutable record of a request for human intervention.
    Generated when escalation is required.
    """
    id: UUID
    envelope: InteractionEnvelope
    autonomy_state: AutonomyState
    policy_decision: PolicyDecision
    justification: str
    created_at: datetime