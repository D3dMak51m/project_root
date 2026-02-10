from abc import ABC, abstractmethod
from typing import List
from src.core.ledger.budget_event import BudgetEvent

class BudgetLedger(ABC):
    """
    Append-only log of budget events.
    Global scope (not context-scoped).
    """
    @abstractmethod
    def record(self, event: BudgetEvent) -> None:
        pass

    @abstractmethod
    def get_history(self) -> List[BudgetEvent]:
        pass