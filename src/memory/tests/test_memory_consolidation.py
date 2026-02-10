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
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext, ConsolidationMode
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
    context = MemoryConsolidationContext(policy, ConsolidationMode.CONSERVATIVE, datetime.now(timezone.utc), False)
    consolidator = MemoryConsolidator()

    events = [create_event(ExecutionStatus.SUCCESS, i) for i in range(10)]
    # Sorted by time (oldest first in list_all usually, but create_event makes newer ones first if offset increases?
    # offset 0 = now. offset 9 = old.
    # We want oldest first for stable sort test.
    events.reverse()

    consolidated = consolidator.consolidate(events, context)

    assert len(consolidated) == 5
    # Should keep most recent
    assert consolidated[-1].issued_at > consolidated[0].issued_at


def test_consolidator_failure_retention():
    policy = MemoryRetentionPolicy(max_events_per_context=10, retain_last_n_failures=3)
    context = MemoryConsolidationContext(policy, ConsolidationMode.CONSERVATIVE, datetime.now(timezone.utc), False)
    consolidator = MemoryConsolidator()

    # 5 failures, 5 successes
    failures = [create_event(ExecutionStatus.FAILED, i) for i in range(5)]
    successes = [create_event(ExecutionStatus.SUCCESS, i + 10) for i in range(5)]
    events = failures + successes

    consolidated = consolidator.consolidate(events, context)

    # Should keep 3 failures + 5 successes = 8 total ( < max 10)
    # Wait, logic: failures_to_keep = last 3. successes_to_keep = all 5. others = 0.
    # Total 8.

    cnt_fail = sum(1 for e in consolidated if e.execution_status == ExecutionStatus.FAILED)
    assert cnt_fail == 3


def test_consolidator_off():
    policy = MemoryRetentionPolicy(max_events_per_context=1)
    context = MemoryConsolidationContext(policy, ConsolidationMode.OFF, datetime.now(timezone.utc), False)
    consolidator = MemoryConsolidator()

    events = [create_event(ExecutionStatus.SUCCESS) for _ in range(5)]
    consolidated = consolidator.consolidate(events, context)

    assert len(consolidated) == 5