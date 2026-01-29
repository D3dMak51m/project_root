from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID
from src.core.domain.resource import StrategicResourceBudget

@dataclass(frozen=True)
class BudgetSnapshot:
    """
    Immutable snapshot of the global strategic resource budget.
    Used for persistence and replay.
    """
    budget: StrategicResourceBudget
    timestamp: datetime
    last_event_id: Optional[UUID] = None
    version: str = "1.1"