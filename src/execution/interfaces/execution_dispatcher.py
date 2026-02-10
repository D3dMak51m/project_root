from abc import ABC, abstractmethod
from src.autonomy.domain.execution_command import ExecutionCommand
from src.core.domain.execution_result import ExecutionResult

class ExecutionDispatcher(ABC):
    """
    Interface for dispatching authorized execution commands to external adapters.
    Must be pure regarding system state (no side effects on core).
    """
    @abstractmethod
    def dispatch(self, command: ExecutionCommand) -> ExecutionResult:
        pass