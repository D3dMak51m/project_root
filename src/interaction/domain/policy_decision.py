from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class PolicyDecision:
    """
    Immutable verdict from the Interaction Policy Engine.
    Determines if an interaction is allowed to proceed to execution/scheduling.
    """
    allowed: bool
    reason: str
    constraints: List[str] = field(default_factory=list) # e.g., "rate_limit_applied", "requires_approval"