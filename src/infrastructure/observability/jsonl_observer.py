import json
import os
from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.observability.strategic_observer import StrategicObserver
from src.core.ledger.strategic_event import StrategicEvent
from src.core.ledger.budget_event import BudgetEvent
from src.core.domain.execution_result import ExecutionResult
from src.core.observability.telemetry_event import TelemetryEvent


class JsonlStrategicObserver(StrategicObserver):
    """
    Production-grade observer that writes structured events to a JSONL file.
    Handles serialization safely.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "value"):  # Enum
            return obj.value
        return str(obj)

    def _write(self, category: str, data: Any, is_replay: bool):
        # In production, we might skip replay events to avoid noise,
        # or tag them. Here we tag them.
        entry = {
            "timestamp": datetime.utcnow().isoformat(),  # Observer time (wall clock)
            "category": category,
            "is_replay": is_replay,
            "data": data
        }

        try:
            with open(self.file_path, 'a') as f:
                f.write(json.dumps(entry, default=self._serialize) + "\n")
        except Exception as e:
            # Observer must NEVER crash the app
            print(f"Observer write failed: {e}")

    def on_strategic_event(self, event: StrategicEvent, is_replay: bool = False) -> None:
        self._write("STRATEGIC", event.__dict__, is_replay)

    def on_budget_event(self, event: BudgetEvent, is_replay: bool = False) -> None:
        self._write("BUDGET", event.__dict__, is_replay)

    def on_execution_result(self, result: ExecutionResult, is_replay: bool = False) -> None:
        self._write("EXECUTION", result.__dict__, is_replay)

    def on_telemetry(self, event: TelemetryEvent) -> None:
        self._write("TELEMETRY", event.__dict__, event.is_replay)