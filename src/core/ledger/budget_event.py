from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

@dataclass(frozen=True)
class BudgetEvent:
    """
    Immutable record of a budget change.
    Ensures deterministic replay of resource state.
    """
    id: UUID
    timestamp: datetime
    event_type: str  # "BUDGET_RECOVERED", "BUDGET_RESERVED", "BUDGET_ROLLED_BACK"
    delta: Dict[str, float] # e.g. {"energy": 10.0, "slots": 1}
    reason: str