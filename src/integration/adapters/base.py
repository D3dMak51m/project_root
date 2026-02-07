from abc import ABC, abstractmethod
from datetime import datetime
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.interaction.domain.intent import InteractionIntent
from src.core.domain.execution_result import ExecutionResult, ExecutionFailureType
from src.integration.normalizer import ResultNormalizer


class BasePlatformAdapter(ExecutionAdapter, ABC):
    """
    Base class for platform-specific adapters.
    Handles common normalization and error trapping.
    """

    def execute(self, intent: InteractionIntent) -> ExecutionResult:
        try:
            return self._perform_execution(intent)
        except Exception as e:
            return ResultNormalizer.failure(
                reason=f"Unhandled adapter exception: {str(e)}",
                failure_type=ExecutionFailureType.INTERNAL
            )

    @abstractmethod
    def _perform_execution(self, intent: InteractionIntent) -> ExecutionResult:
        pass