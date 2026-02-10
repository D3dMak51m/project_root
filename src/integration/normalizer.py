from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType


class ResultNormalizer:
    """
    Normalizes external chaos into canonical ExecutionResult objects.
    """

    @staticmethod
    def success(
            effects: List[str],
            costs: Dict[str, float],
            observations: Dict[str, Any],
            timestamp: Optional[datetime] = None
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            timestamp=timestamp or datetime.now(timezone.utc),
            effects=effects,
            costs=costs,
            observations=observations,
            failure_type=ExecutionFailureType.NONE
        )

    @staticmethod
    def failure(
            reason: str,
            failure_type: ExecutionFailureType = ExecutionFailureType.ENVIRONMENT,
            costs: Dict[str, float] = None,
            timestamp: Optional[datetime] = None
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            timestamp=timestamp or datetime.now(timezone.utc),
            failure_type=failure_type,
            reason=reason,
            costs=costs or {}
        )

    @staticmethod
    def rejection(
            reason: str,
            timestamp: Optional[datetime] = None
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.REJECTED,
            timestamp=timestamp or datetime.now(timezone.utc),
            failure_type=ExecutionFailureType.POLICY,
            reason=reason
        )