from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Optional
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.governance_action import GovernanceAction

@dataclass(frozen=True)
class AdminCommand:
    """
    Represents an external instruction from a human administrator.
    """
    id: UUID
    action: GovernanceAction
    scope: GovernanceScope
    target_id: Optional[str] = None # e.g., escalation_id, policy_id
    payload: Dict[str, Any] = field(default_factory=dict)
    issued_by: str = "admin"
    issued_at: datetime = field(default_factory=datetime.utcnow)