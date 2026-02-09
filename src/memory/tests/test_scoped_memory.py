import pytest
from uuid import uuid4
from datetime import datetime, timezone
from src.memory.store.memory_store import MemoryStore
from src.memory.services.memory_scope_resolver import MemoryScopeResolver
from src.memory.domain.event_record import EventRecord
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.domain.governance_snapshot import GovernanceSnapshot


def create_event(domain: str) -> EventRecord:
    return EventRecord(
        id=uuid4(),
        intent_id=uuid4(),
        execution_status=ExecutionStatus.SUCCESS,
        execution_result=None,
        autonomy_state_before=AutonomyState(AutonomyMode.READY, "", 0.0, [], False),
        policy_decision=PolicyDecision(True, "", []),
        governance_snapshot=GovernanceSnapshot.empty(),
        issued_at=datetime.now(timezone.utc),
        context_domain=domain
    )


def test_scope_resolution():
    store = MemoryStore()
    resolver = MemoryScopeResolver(store)

    e1 = create_event("social")
    e2 = create_event("finance")
    e3 = create_event("social")

    store.append(e1)
    store.append(e2)
    store.append(e3)

    context_social = StrategicContext("global", None, None, "social")
    view_social = resolver.resolve(context_social)

    assert len(view_social.events) == 2
    assert e1 in view_social.events
    assert e3 in view_social.events
    assert e2 not in view_social.events

    context_finance = StrategicContext("global", None, None, "finance")
    view_finance = resolver.resolve(context_finance)

    assert len(view_finance.events) == 1
    assert view_finance.events[0] == e2