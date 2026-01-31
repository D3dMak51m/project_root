from abc import ABC, abstractmethod
from datetime import datetime
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult, ExecutionFailureType
from src.integration.normalizer import ResultNormalizer


class BasePlatformAdapter(ExecutionAdapter, ABC):
    """
    Base class for platform-specific adapters.
    Handles common normalization and error trapping.
    """

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        # Note: TimeSource is not injected here directly to keep adapter interface simple.
        # The orchestrator or normalizer handles timestamping if needed,
        # but here we rely on the normalizer's default or passed time.
        # For strict determinism, the orchestrator should pass 'now' to execute,
        # but changing ExecutionAdapter.execute signature breaks C.11 contract.
        # FIX: We assume the adapter operates in "now" (runtime), and the result's timestamp
        # is captured at the moment of execution. Determinism is handled by how this result
        # is *ingested* (via LifeSignals), not how it's created.
        # However, ResultNormalizer needs a timestamp.
        # We will use datetime.now(timezone.utc) here because this IS the boundary to the real world.
        # The Core will treat this timestamp as data.

        try:
            return self._perform_execution(intent)
        except Exception as e:
            return ResultNormalizer.failure(
                reason=f"Unhandled adapter exception: {str(e)}",
                failure_type=ExecutionFailureType.INTERNAL
            )

    @abstractmethod
    def _perform_execution(self, intent: ExecutionIntent) -> ExecutionResult:
        pass