from abc import ABC, abstractmethod
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult

class ExecutionAdapter(ABC):
    """
    Boundary interface for executing intents in the external world.
    Isolates the core from implementation details of tools, APIs, or simulations.
    """
    @abstractmethod
    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        """
        Execute the given intent and return a structured result.
        Must handle all exceptions internally and return a valid ExecutionResult.
        """
        pass