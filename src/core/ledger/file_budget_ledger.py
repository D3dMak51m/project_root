import json
import os
from typing import List
from datetime import datetime
from uuid import UUID

from src.core.ledger.budget_ledger import BudgetLedger
from src.core.ledger.budget_event import BudgetEvent


class FileBudgetLedger(BudgetLedger):
    """
    File-backed append-only log of budget events.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write("")

    def record(self, event: BudgetEvent) -> None:
        data = {
            "id": str(event.id),
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "delta": event.delta,
            "reason": event.reason
        }
        with open(self.file_path, 'a') as f:
            f.write(json.dumps(data) + "\n")

    def get_history(self) -> List[BudgetEvent]:
        events = []
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    event = BudgetEvent(
                        id=UUID(data['id']),
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        event_type=data['event_type'],
                        delta=data['delta'],
                        reason=data['reason']
                    )
                    events.append(event)
                except json.JSONDecodeError:
                    continue
        return events