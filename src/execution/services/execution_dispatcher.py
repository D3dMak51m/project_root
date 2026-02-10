from src.execution.interfaces.execution_dispatcher import ExecutionDispatcher
from src.autonomy.domain.execution_command import ExecutionCommand
from src.core.domain.execution_result import ExecutionResult, ExecutionFailureType
from src.integration.registry import ExecutionAdapterRegistry
from src.integration.normalizer import ResultNormalizer


class StandardExecutionDispatcher(ExecutionDispatcher):
    """
    Deterministic dispatcher that routes commands to registered adapters.
    Handles adapter resolution and error trapping.
    """

    def __init__(self, registry: ExecutionAdapterRegistry):
        self.registry = registry

    def dispatch(self, command: ExecutionCommand) -> ExecutionResult:
        # 1. Extract Intent directly from command envelope
        interaction_intent = command.envelope.intent

        # 2. Resolve Adapter using InteractionIntent
        adapter = self.registry.resolve(interaction_intent)

        if not adapter:
            return ResultNormalizer.failure(
                reason=f"No adapter found for intent type: {interaction_intent.type}",
                failure_type=ExecutionFailureType.INTERNAL
            )

        # 3. Execute
        try:
            return adapter.execute(interaction_intent)
        except Exception as e:
            # Catch-all for unexpected adapter crashes
            return ResultNormalizer.failure(
                reason=f"Dispatcher caught exception: {str(e)}",
                failure_type=ExecutionFailureType.INTERNAL
            )