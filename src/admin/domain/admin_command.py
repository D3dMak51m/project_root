from dataclasses import dataclass, field
from uuid import UUID
from typing import Dict, Any, Optional
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.governance_action import GovernanceAction

@dataclass(frozen=True)
class AdminCommand:
    """
    Represents an external instruction from a human administrator.
    Does NOT carry authoritative timestamp or ID generation logic.
    """
    id: Optional[UUID] # Client-provided ID or None
    action: GovernanceAction
    scope: GovernanceScope
    target_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    issued_by: str = "admin"
    # issued_at removed to enforce GovernanceService as sole time authority