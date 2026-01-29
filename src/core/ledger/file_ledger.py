import json
import os
from typing import List
from datetime import datetime
from uuid import UUID

from src.core.ledger.strategic_ledger import StrategicLedger
from src.core.ledger.strategic_event import StrategicEvent
from src.core.domain.strategic_context import StrategicContext


class FileStrategicLedger(StrategicLedger):
    """
    File-backed append-only log of strategic events.
    Ensures events persist across process restarts for true replay testing.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # Ensure file exists
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write("")

    def record(self, event: StrategicEvent) -> None:
        # Serialize event to JSON line
        data = {
            "id": str(event.id),
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "details": event.details,
            # We store context as string representation for simple filtering in this implementation
            # In production, this might be structured.
            "context_key": str(event.context)
        }
        with open(self.file_path, 'a') as f:
            f.write(json.dumps(data) + "\n")

    def get_history(self, context: StrategicContext) -> List[StrategicEvent]:
        events = []
        target_key = str(context)

        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("context_key") == target_key:
                        # Reconstruct context object?
                        # For E.4/E.5 replay, we need the event object.
                        # The context object inside event is used by some consumers?
                        # StrategicEvent definition has 'context: StrategicContext'.
                        # We need to reconstruct it or pass the requested context.
                        # Since get_history is scoped to 'context', we can reuse the passed context object
                        # for the event reconstruction to satisfy type checker, assuming strict isolation.

                        event = StrategicEvent(
                            id=UUID(data['id']),
                            timestamp=datetime.fromisoformat(data['timestamp']),
                            event_type=data['event_type'],
                            details=data['details'],
                            context=context
                        )
                        events.append(event)
                except json.JSONDecodeError:
                    continue
        return events