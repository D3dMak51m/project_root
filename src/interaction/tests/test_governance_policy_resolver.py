import pytest
import random
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from src.interaction.domain.policy_decision import PolicyDecision
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.interaction.services.governance_policy_resolver import StandardGovernancePolicyResolver
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext


def create_decision(action: GovernanceAction, scope: GovernanceScope, effect=None, time_offset=0) -> GovernanceDecision:
    return GovernanceDecision(
        id=uuid4(), command_id=uuid4(), action=action, scope=scope,
        justification="test", issued_at=datetime.now(timezone.utc) + timedelta(seconds=time_offset), effect=effect or {}
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
    context = RuntimeGovernanceContext.build(sorted(decisions, key=lambda d: d.issued_at))

    result = resolver.apply(policy, context)

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
    context_1 = RuntimeGovernanceContext.build(sorted(decisions, key=lambda d: d.issued_at))

    res1 = resolver.apply(policy, context_1)

    random.shuffle(decisions)
    context_2 = RuntimeGovernanceContext.build(sorted(decisions, key=lambda d: d.issued_at))
    res2 = resolver.apply(policy, context_2)

    assert res1 == res2
    # Constraints should be appended in deterministic order
    assert res1.constraints == ["c1", "c2"]
