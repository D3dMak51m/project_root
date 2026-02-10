import pytest
import random
from uuid import uuid4
from datetime import datetime, timedelta
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.autonomy.services.governance_autonomy_resolver import StandardGovernanceAutonomyResolver


def create_decision(action: GovernanceAction, scope: GovernanceScope, effect=None, time_offset=0) -> GovernanceDecision:
    return GovernanceDecision(
        id=uuid4(), command_id=uuid4(), action=action, scope=scope,
        justification="test", issued_at=datetime.utcnow() + timedelta(seconds=time_offset), effect=effect or {}
    )


def test_resolver_determinism_shuffled():
    resolver = StandardGovernanceAutonomyResolver()
    state = AutonomyState(AutonomyMode.READY, "test", 0.5, [], False)

    d1 = create_decision(GovernanceAction.LOCK_AUTONOMY, GovernanceScope.AUTONOMY, time_offset=10)
    d2 = create_decision(GovernanceAction.UNLOCK_AUTONOMY, GovernanceScope.AUTONOMY, time_offset=20)
    d3 = create_decision(GovernanceAction.OVERRIDE_MODE, GovernanceScope.AUTONOMY, {"mode": "SILENT"}, time_offset=30)

    decisions = [d1, d2, d3]

    # Run multiple times with shuffled input
    for _ in range(10):
        shuffled = decisions.copy()
        random.shuffle(shuffled)
        result = resolver.apply(state, shuffled)

        # Logic: Lock -> Unlock -> Override(Silent)
        # Final state should be SILENT
        assert result.mode == AutonomyMode.SILENT


def test_unlock_restores_state():
    resolver = StandardGovernanceAutonomyResolver()
    state = AutonomyState(AutonomyMode.READY, "test", 0.5, [], False)

    # Lock then Unlock
    d1 = create_decision(GovernanceAction.LOCK_AUTONOMY, GovernanceScope.AUTONOMY, time_offset=10)
    d2 = create_decision(GovernanceAction.UNLOCK_AUTONOMY, GovernanceScope.AUTONOMY, time_offset=20)

    result = resolver.apply(state, [d1, d2])

    # Should be back to original state (READY)
    assert result.mode == AutonomyMode.READY
    assert "governance_lock" not in result.constraints


def test_lock_overrides_override():
    resolver = StandardGovernanceAutonomyResolver()
    state = AutonomyState(AutonomyMode.READY, "test", 0.5, [], False)

    # Override then Lock
    d1 = create_decision(GovernanceAction.OVERRIDE_MODE, GovernanceScope.AUTONOMY, {"mode": "SILENT"}, time_offset=10)
    d2 = create_decision(GovernanceAction.LOCK_AUTONOMY, GovernanceScope.AUTONOMY, time_offset=20)

    result = resolver.apply(state, [d1, d2])

    assert result.mode == AutonomyMode.BLOCKED