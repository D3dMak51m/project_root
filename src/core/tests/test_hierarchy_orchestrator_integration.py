from datetime import datetime, timezone
from uuid import uuid4

from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionFailureType, ExecutionResult, ExecutionStatus
from src.core.domain.resource import ResourceCost
from src.core.domain.strategic_context import StrategicContext
from src.core.ledger.in_memory_ledger import InMemoryStrategicLedger
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.persistence.in_memory_backend import InMemoryStrategicStateBackend
from src.core.time.frozen_time_source import FrozenTimeSource


class _AggRecorder:
    def __init__(self):
        self.exec_rows = []
        self.cf_rows = []

    def record_execution(self, context_domain, result, reservation_delta=None, queue_lag=0.0):
        self.exec_rows.append((context_domain, result.status, dict(reservation_delta or {}), queue_lag))

    def record_counterfactual(self, context_domain, stage, reason):
        self.cf_rows.append((context_domain, stage, reason))


def _intent(now: datetime):
    return ExecutionIntent(
        id=uuid4(),
        commitment_id=uuid4(),
        intention_id=uuid4(),
        persona_id=uuid4(),
        abstract_action="communicate",
        constraints={"platform": "telegram", "target_id": "chat-1", "text": "hello"},
        created_at=now,
        reversible=False,
        risk_level=0.1,
        estimated_cost=ResourceCost(1.0, 1.0, 1),
    )


def test_orchestrator_reports_execution_and_counterfactual_to_upward_aggregation():
    now = datetime(2025, 2, 8, tzinfo=timezone.utc)
    agg = _AggRecorder()
    orchestrator = StrategicOrchestrator(
        time_source=FrozenTimeSource(now),
        ledger=InMemoryStrategicLedger(),
        backend=InMemoryStrategicStateBackend(),
        upward_aggregation_service=agg,
    )
    intent = _intent(now)
    context_domain = "telegram:chat-1"

    orchestrator.post_execution_pipeline(
        {
            "intent_id": intent.id,
            "intent": intent,
            "context_domain": context_domain,
            "reservation_delta": {"energy_budget": -1.0},
            "result": ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                timestamp=now,
                effects=["message_sent"],
                observations={"message_id": 1},
                failure_type=ExecutionFailureType.NONE,
            ),
        }
    )

    orchestrator._record_counterfactual(
        intent=intent,
        reason="test_reason",
        stage="Arbitration",
        gov_context=None,
        context=StrategicContext(country="global", region=None, goal_id=None, domain=context_domain),
        now=now,
    )

    assert len(agg.exec_rows) == 1
    assert agg.exec_rows[0][0] == context_domain
    assert len(agg.cf_rows) == 1
    assert agg.cf_rows[0][1] == "Arbitration"

