import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from src.memory.domain.event_record import EventRecord
from src.memory.domain.governance_snapshot import GovernanceSnapshot
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.domain.memory_retention_policy import MemoryRetentionPolicy
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext
from src.memory.services.memory_consolidator import MemoryConsolidator


def create_event(status: ExecutionStatus, time_offset: int = 0) -> EventRecord:
    return EventRecord(
        id=uuid4(),
        intent_id=uuid4(),
        execution_status=status,
        execution_result=ExecutionResult(status, datetime.now(timezone.utc), failure_type=ExecutionFailureType.NONE),
        autonomy_state_before=AutonomyState(AutonomyMode.READY, "", 0.0, [], False),
        policy_decision=PolicyDecision(True, "", []),
        governance_snapshot=GovernanceSnapshot.empty(),
        issued_at=datetime.now(timezone.utc) - timedelta(seconds=time_offset),
        context_domain="test"
    )


def test_consolidator_cap():
    policy = MemoryRetentionPolicy(max_events_per_context=5)
    context = MemoryConsolidationContext(policy, datetime.now(timezone.utc))
    consolidator = MemoryConsolidator()

    events = [create_event(ExecutionStatus.SUCCESS, i) for i in range(10)]
    # Ensure sorted input for deterministic test
    events.sort(key=lambda e: e.issued_at)

    consolidated = consolidator.consolidate(events, context)

    assert len(consolidated) == 5
    # Should keep most recent (last 5)
    assert consolidated[0].issued_at < consolidated[-1].issued_at
    # The oldest retained event should be newer than the dropped ones
    # (Assuming time_offset increases into past, so smaller offset = newer)
    # events[0] is oldest (offset 9), events[-1] is newest (offset 0)
    # consolidated should be events[5:]
    assert consolidated[0] == events[5]


def test_consolidator_determinism():
    policy = MemoryRetentionPolicy(max_events_per_context=5)
    context = MemoryConsolidationContext(policy, datetime.now(timezone.utc))
    consolidator = MemoryConsolidator()

    events = [create_event(ExecutionStatus.SUCCESS, i) for i in range(10)]

    c1 = consolidator.consolidate(events, context)
    c2 = consolidator.consolidate(events, context)

    assert c1 == c2