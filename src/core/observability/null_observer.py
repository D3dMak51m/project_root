from src.core.observability.strategic_observer import StrategicObserver
from src.core.ledger.strategic_event import StrategicEvent
from src.core.ledger.budget_event import BudgetEvent
from src.core.domain.execution_result import ExecutionResult
from src.core.observability.telemetry_event import TelemetryEvent

class NullStrategicObserver(StrategicObserver):
    """
    Default no-op observer.
    """
    def on_strategic_event(self, event: StrategicEvent, is_replay: bool = False) -> None:
        pass

    def on_budget_event(self, event: BudgetEvent, is_replay: bool = False) -> None:
        pass

    def on_execution_result(self, result: ExecutionResult, is_replay: bool = False) -> None:
        pass

    def on_telemetry(self, event: TelemetryEvent) -> None:
        pass