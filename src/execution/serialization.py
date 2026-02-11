from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict
from uuid import UUID

from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import (
    ExecutionFailureType,
    ExecutionResult,
    ExecutionStatus,
)
from src.core.domain.resource import ResourceCost


def _serialize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


def serialize_intent(intent: ExecutionIntent) -> Dict[str, Any]:
    return _serialize(asdict(intent))


def deserialize_intent(data: Dict[str, Any]) -> ExecutionIntent:
    estimated_cost = data.get("estimated_cost")
    cost_obj = None
    if estimated_cost:
        cost_obj = ResourceCost(
            energy_cost=float(estimated_cost["energy_cost"]),
            attention_cost=float(estimated_cost["attention_cost"]),
            execution_slot_cost=int(estimated_cost.get("execution_slot_cost", 1)),
        )
    return ExecutionIntent(
        id=UUID(data["id"]),
        commitment_id=UUID(data["commitment_id"]),
        intention_id=UUID(data["intention_id"]),
        persona_id=UUID(data["persona_id"]),
        abstract_action=data["abstract_action"],
        constraints=dict(data.get("constraints", {})),
        created_at=datetime.fromisoformat(data["created_at"]),
        reversible=bool(data["reversible"]),
        risk_level=float(data["risk_level"]),
        estimated_cost=cost_obj,
    )


def serialize_result(result: ExecutionResult) -> Dict[str, Any]:
    return _serialize(asdict(result))


def deserialize_result(data: Dict[str, Any]) -> ExecutionResult:
    return ExecutionResult(
        status=ExecutionStatus(data["status"]),
        timestamp=datetime.fromisoformat(data["timestamp"]),
        effects=list(data.get("effects", [])),
        costs=dict(data.get("costs", {})),
        observations=dict(data.get("observations", {})),
        failure_type=ExecutionFailureType(data.get("failure_type", ExecutionFailureType.NONE.value)),
        reason=data.get("reason", ""),
    )
