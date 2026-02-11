import pytest
from uuid import uuid4
from datetime import datetime, timezone
from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.domain.governance_snapshot import GovernanceSnapshot
from src.memory.services.counterfactual_analyzer import CounterfactualAnalyzer
from src.core.domain.execution_intent import ExecutionIntent


def create_cf_event(stage: str, risk: float = 0.1) -> CounterfactualEvent:
    intent = ExecutionIntent(
        id=uuid4(), commitment_id=uuid4(), intention_id=uuid4(), persona_id=uuid4(),
        abstract_action="test", constraints={}, created_at=datetime.now(timezone.utc),
        reversible=False, risk_level=risk, estimated_cost=None
    )
    return CounterfactualEvent(
        id=uuid4(), intent_id=intent.id, intent=intent, reason="test",
        suppression_stage=stage, policy_decision=None,
        governance_snapshot=GovernanceSnapshot.empty(),
        context_domain="test", timestamp=datetime.now(timezone.utc)
    )


def test_analyzer_metrics():
    analyzer = CounterfactualAnalyzer()
    events = [
        create_cf_event("Policy"),
        create_cf_event("Governance"),
        create_cf_event("Arbitration", risk=0.5),
        create_cf_event("Budget")
    ]

    metrics = analyzer.analyze(events, datetime.now(timezone.utc))

    # 2 Gov/Policy blocks out of 4
    assert metrics["governance_friction_index"] == 0.5

    # 1 Policy block out of 4
    assert metrics["policy_conflict_density"] == 0.25

    # Pressure: (0.1 + 0.1 + 0.5 + 0.1) = 0.8. Normalized by (4/10) = 0.4. Result = 2.0?
    # Logic: pressure / max(1, total/10). 0.8 / 1 = 0.8.
    assert metrics["missed_opportunity_pressure"] == pytest.approx(0.8)


def test_empty_analysis():
    analyzer = CounterfactualAnalyzer()
    metrics = analyzer.analyze([], datetime.now(timezone.utc))
    assert metrics["governance_friction_index"] == 0.0
