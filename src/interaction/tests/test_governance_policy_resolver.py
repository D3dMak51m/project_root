import pytest
import random
from uuid import uuid4
from datetime import datetime, timedelta
from src.interaction.domain.policy_decision import PolicyDecision
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.interaction.services.governance_policy_resolver import StandardGovernancePolicyResolver


def create_decision(action: GovernanceAction, scope: GovernanceScope, effect=None, time_offset=0) -> GovernanceDecision:
    return GovernanceDecision(
        id=uuid4(), command_id=uuid4(), action=action, scope=scope,
        justification="test", issued_at=datetime.utcnow() + timedelta(seconds=time_offset), effect=effect or {}
    )


def test_reject_dominance():
    resolver = StandardGovernancePolicyResolver()
    policy = PolicyDecision(True, "OK", [])

    # Constraint then Reject
    d1 = create_decision(GovernanceAction.IMPOSE_CONSTRAINT, GovernanceScope.POLICY, {"constraint": "c1"},
                         time_offset=10)
    d2 = create_decision(GovernanceAction.REJECT, GovernanceScope.POLICY, time_offset=20)

    decisions = [d1, d2]
    random.shuffle(decisions)

    result = resolver.apply(policy, decisions)

    assert not result.allowed
    assert "Governance rejection" in result.reason


def test_determinism_shuffled():
    resolver = StandardGovernancePolicyResolver()
    policy = PolicyDecision(True, "OK", [])

    d1 = create_decision(GovernanceAction.IMPOSE_CONSTRAINT, GovernanceScope.POLICY, {"constraint": "c1"},
                         time_offset=10)
    d2 = create_decision(GovernanceAction.IMPOSE_CONSTRAINT, GovernanceScope.POLICY, {"constraint": "c2"},
                         time_offset=20)

    decisions = [d1, d2]

    res1 = resolver.apply(policy, decisions)

    random.shuffle(decisions)
    res2 = resolver.apply(policy, decisions)

    assert res1 == res2
    # Constraints should be appended in deterministic order
    assert res1.constraints == ["c1", "c2"]