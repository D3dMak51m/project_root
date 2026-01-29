from datetime import datetime, timezone
from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType


class MockExecutionAdapter(ExecutionAdapter):
    """
    Mock implementation for testing and development.
    Simulates execution outcomes based on intent properties or random logic.
    """

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        # Simulate success for "communicate" action
        if intent.abstract_action == "communicate":
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                timestamp=datetime.now(timezone.utc),
                effects=["message_sent"],
                costs={"energy": 5.0},
                observations={"reply_count": 0},
                failure_type=ExecutionFailureType.NONE
            )

        # Simulate failure for high risk actions
        if intent.risk_level > 0.8:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                timestamp=datetime.now(timezone.utc),
                failure_type=ExecutionFailureType.ENVIRONMENT,
                reason="Risk too high for environment",
                costs={"energy": 2.0}
            )

        # Default success
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(timezone.utc),
            effects=["action_completed"],
            costs={"energy": 1.0},
            failure_type=ExecutionFailureType.NONE
        )