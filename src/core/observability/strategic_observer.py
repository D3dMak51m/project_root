from abc import ABC, abstractmethod
from src.core.ledger.strategic_event import StrategicEvent
from src.core.ledger.budget_event import BudgetEvent
from src.core.domain.execution_result import ExecutionResult
from src.core.observability.telemetry_event import TelemetryEvent


class StrategicObserver(ABC):
    """
    Hook interface for observing strategic events and telemetry.
    Implementations must not have side effects on the core logic.
    """

    @abstractmethod
    def on_strategic_event(self, event: StrategicEvent, is_replay: bool = False) -> None:
        """Called when a core strategic event occurs (e.g. mode shift)."""
        pass

    @abstractmethod
    def on_budget_event(self, event: BudgetEvent, is_replay: bool = False) -> None:
        """Called when a budget event occurs (e.g. reservation)."""
        pass

    @abstractmethod
    def on_execution_result(self, result: ExecutionResult, is_replay: bool = False) -> None:
        """Called when an execution attempt completes."""
        pass

    @abstractmethod
    def on_telemetry(self, event: TelemetryEvent) -> None:
        """Called for generic telemetry (metrics, traces)."""
        pass