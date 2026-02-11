from datetime import datetime, timezone
from uuid import uuid4

from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.autonomy.domain.autonomy_state import AutonomyState
from src.core.domain.execution_result import ExecutionStatus
from src.interaction.domain.interaction_event import InteractionEvent
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.domain.event_record import EventRecord
from src.memory.domain.governance_snapshot import GovernanceSnapshot
from src.memory.store.memory_store import MemoryStore
from src.persistence.drift_detector import detect_memory_drift, detect_world_observation_drift
from src.persistence.dual_write import CutoverPhase, DualWriteConfig, DualWriteContextBuffer, DualWriteMemoryStore
from src.world.context.context_buffer import ContextBuffer
from src.world.domain.world_observation import WorldObservation
from src.world.store.world_observation_store import WorldObservationStore


def _event(context_domain: str) -> EventRecord:
    now = datetime.now(timezone.utc)
    return EventRecord(
        id=uuid4(),
        intent_id=uuid4(),
        execution_status=ExecutionStatus.SUCCESS,
        execution_result=None,
        autonomy_state_before=AutonomyState(AutonomyMode.READY, "ok", 0.1),
        policy_decision=PolicyDecision(True, "ok", []),
        governance_snapshot=GovernanceSnapshot.empty(),
        issued_at=now,
        context_domain=context_domain,
    )


def _observation(context_domain: str, user_id: str) -> WorldObservation:
    now = datetime.now(timezone.utc)
    interaction = InteractionEvent(
        id=uuid4(),
        platform="telegram",
        user_id=user_id,
        chat_id=context_domain.split(":")[-1],
        content="hello",
        message_type="text",
        timestamp=now,
        raw_metadata={},
    )
    return WorldObservation(interaction=interaction, context_domain=context_domain)


def test_dual_write_memory_store_and_drift_detector_are_consistent():
    memory_primary = MemoryStore()
    memory_secondary = MemoryStore()
    config = DualWriteConfig(phase=CutoverPhase.PHASE_1_DUAL_WRITE)
    dual = DualWriteMemoryStore(memory_primary, memory_secondary, config=config)

    dual.append(_event("telegram:chat-1"))
    dual.append(_event("telegram:chat-2"))

    assert len(memory_primary.list_all()) == 2
    assert len(memory_secondary.list_all()) == 2

    report = detect_memory_drift(memory_primary, memory_secondary)
    assert report.clean

    config.phase = CutoverPhase.PHASE_2_POSTGRES_READ_PRIMARY
    assert len(dual.list_all()) == 2


def test_dual_write_context_buffer_switches_read_primary_across_cutover_phases():
    memory_buffer = ContextBuffer()
    persistent_buffer = ContextBuffer()
    config = DualWriteConfig(phase=CutoverPhase.PHASE_1_DUAL_WRITE)
    dual = DualWriteContextBuffer(memory_buffer, persistent_buffer, config=config)

    first = _observation("telegram:chat-a", "user-a")
    dual.add(first)
    assert memory_buffer.depth() == 1
    assert persistent_buffer.depth() == 1

    popped_phase1 = dual.pop_all()
    assert len(popped_phase1) == 1
    assert popped_phase1[0].interaction.user_id == "user-a"
    assert memory_buffer.depth() == 0
    assert persistent_buffer.depth() == 0

    config.phase = CutoverPhase.PHASE_2_POSTGRES_READ_PRIMARY
    second = _observation("telegram:chat-b", "user-b")
    dual.add(second)
    popped_phase2 = dual.pop_all()
    assert len(popped_phase2) == 1
    assert popped_phase2[0].interaction.user_id == "user-b"
    assert memory_buffer.depth() == 0
    assert persistent_buffer.depth() == 0


def test_world_observation_drift_detector_matches_equal_stores():
    left = WorldObservationStore()
    right = WorldObservationStore()

    obs = _observation("telegram:chat-77", "user-77")
    left.append(obs)
    right.append(obs)

    report = detect_world_observation_drift(left, right, context_domain="telegram:chat-77")
    assert report.clean
