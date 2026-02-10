import pytest
import random
from uuid import uuid4
from datetime import datetime, timedelta
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.autonomy.services.governance_execution_resolver import StandardGovernanceExecutionResolver


def create_decision(action: GovernanceAction, scope: GovernanceScope, effect=None, time_offset=0) -> GovernanceDecision:
    return GovernanceDecision(
        id=uuid4(), command_id=uuid4(), action=action, scope=scope,
        justification="test", issued_at=datetime.utcnow() + timedelta(seconds=time_offset), effect=effect or {}
    )


def test_determinism_shuffled():
    resolver = StandardGovernanceExecutionResolver()
    gate = ExecutionGateDecision.ALLOW

    # Lock then Unlock (if unlock was supported here, but execution resolver is simpler)
    # Let's test multiple locks
    d1 = create_decision(GovernanceAction.LOCK_AUTONOMY, GovernanceScope.GLOBAL, time_offset=10)
    d2 = create_decision(GovernanceAction.IMPOSE_CONSTRAINT, GovernanceScope.GLOBAL, {"constraint": "EMERGENCY_STOP"},
                         time_offset=20)

    decisions = [d1, d2]

    for _ in range(10):
        random.shuffle(decisions)
        result = resolver.apply(gate, decisions)
        assert result == ExecutionGateDecision.DENY


def test_global_lock_priority():
    resolver = StandardGovernanceExecutionResolver()
    gate = ExecutionGateDecision.ALLOW
    decisions = [create_decision(GovernanceAction.LOCK_AUTONOMY, GovernanceScope.GLOBAL)]

    result = resolver.apply(gate, decisions)
    assert result == ExecutionGateDecision.DENY