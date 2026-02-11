import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.memory.domain.event_record import EventRecord
from src.memory.domain.governance_snapshot import GovernanceSnapshot
from src.memory.store.memory_store import MemoryStore
from src.memory.services.memory_ingestion import MemoryIngestionService
from src.memory.services.memory_query import MemoryQueryService
from src.memory.store.memory_index import MemoryIndex
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.policy_decision import PolicyDecision

# --- Helpers ---

FIXED_TIME = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def create_event(status: ExecutionStatus, intent_id: UUID = None) -> EventRecord:
    return EventRecord(
        id=uuid4(),
        intent_id=intent_id or uuid4(),
        execution_status=status,
        execution_result=ExecutionResult(status, FIXED_TIME, failure_type=ExecutionFailureType.NONE),
        autonomy_state_before=AutonomyState(AutonomyMode.READY, "test", 0.5, [], False),
        policy_decision=PolicyDecision(True, "OK", []),
        governance_snapshot=GovernanceSnapshot.empty(),
        issued_at=FIXED_TIME,
        context_domain="test"
    )


# --- Tests ---

def test_memory_ingestion_and_query():
    store = MemoryStore()
    ingestion = MemoryIngestionService(store)
    query = MemoryQueryService(store)

    event1 = create_event(ExecutionStatus.SUCCESS)
    event2 = create_event(ExecutionStatus.FAILED)

    ingestion.ingest(event1)
    ingestion.ingest(event2)

    assert len(store.list_all()) == 2
    assert query.last_n_events(1)[0] == event2
    # last_successful_event returns Optional[EventRecord]
    assert query.last_successful_event() == event1
    assert len(query.recent_failures(5)) == 1
    assert query.recent_failures(5)[0] == event2


def test_determinism():
    store = MemoryStore()
    ingestion = MemoryIngestionService(store)

    event = create_event(ExecutionStatus.SUCCESS)

    ingestion.ingest(event)

    # Same input -> Same state
    assert store.list_all()[0] == event


def test_by_intent_query():
    store = MemoryStore()
    ingestion = MemoryIngestionService(store)
    query = MemoryQueryService(store)

    intent_id = uuid4()
    event1 = create_event(ExecutionStatus.SUCCESS, intent_id)
    event2 = create_event(ExecutionStatus.FAILED, intent_id)

    ingestion.ingest(event1)
    ingestion.ingest(event2)

    found = query.by_intent(intent_id)
    assert len(found) == 2
    assert found[0] == event1
    assert found[1] == event2

    not_found = query.by_intent(uuid4())
    assert len(not_found) == 0


def test_memory_index():
    store = MemoryStore()
    ingestion = MemoryIngestionService(store)
    index = MemoryIndex(store)

    intent_id = uuid4()
    event = create_event(ExecutionStatus.SUCCESS, intent_id)
    ingestion.ingest(event)

    intent_idx = index.build_intent_index()
    assert len(intent_idx[intent_id]) == 1

    status_idx = index.build_status_index()
    assert len(status_idx["SUCCESS"]) == 1
