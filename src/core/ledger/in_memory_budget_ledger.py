from typing import List
from src.core.ledger.budget_ledger import BudgetLedger
from src.core.ledger.budget_event import BudgetEvent

class InMemoryBudgetLedger(BudgetLedger):
    def __init__(self):
        self._events: List[BudgetEvent] = []

    def record(self, event: BudgetEvent) -> None:
        self._events.append(event)

    def get_history(self) -> List[BudgetEvent]:
        return list(self._events)