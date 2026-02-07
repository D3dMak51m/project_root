from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime
from typing import Dict, Any
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.governance_action import GovernanceAction

@dataclass(frozen=True)
class GovernanceDecision:
    """
    Immutable result of processing an AdminCommand.
    Represents the system's acceptance and enactment of a governance instruction.
    """
    id: UUID
    command_id: UUID
    action: GovernanceAction
    scope: GovernanceScope
    justification: str
    issued_at: datetime
    effect: Dict[str, Any] = field(default_factory=dict)
    issued_by: str = "governance_service"