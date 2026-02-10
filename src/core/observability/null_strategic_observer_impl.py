from src.core.observability.strategic_observer import StrategicObserver
from src.core.observability.telemetry_event import TelemetryEvent
from src.core.ledger.budget_event import BudgetEvent
from src.core.domain.execution_result import ExecutionResult

class NullStrategicObserverImpl(StrategicObserver):
    """
    Concrete no-op observer.
    Required for dev/bootstrap and headless execution.
    Does not record, log, or emit anything.
    """

    def on_budget_event(self, event: BudgetEvent, is_replay: bool) -> None:
        pass

    def on_execution_result(self, result: ExecutionResult, is_replay: bool) -> None:
        pass

    def on_strategic_event(self, event_type: str, payload: dict, is_replay: bool) -> None:
        pass

    def on_telemetry(self, event: TelemetryEvent) -> None:
        pass
