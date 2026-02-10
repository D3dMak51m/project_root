from datetime import datetime, timezone
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType


class MockExecutionAdapter(ExecutionAdapter):
    """
    Mock implementation for testing and development.
    """

    def execute(self, intent: InteractionIntent) -> ExecutionResult:
        # Simulate success for MESSAGE type
        if intent.type == InteractionType.MESSAGE:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                timestamp=datetime.now(timezone.utc),
                effects=["message_sent"],
                costs={"energy": 5.0},
                observations={"reply_count": 0},
                failure_type=ExecutionFailureType.NONE
            )

        # Default success
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(timezone.utc),
            effects=["action_completed"],
            costs={"energy": 1.0},
            failure_type=ExecutionFailureType.NONE
        )