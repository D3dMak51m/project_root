from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(frozen=True)
class ExecutionEligibilityResult:
    """
    Value object representing the verdict of eligibility evaluation.
    Read-only, carries no authority.
    """
    allow: bool
    reason: str
    cooldown_until: Optional[datetime] = None
    risk_blocked: bool = False