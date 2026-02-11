from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.admin.services.control_plane_service import AdminControlPlaneService
from src.core.domain.behavior import BehaviorState
from src.core.domain.entity import AIHuman
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.identity import Identity
from src.core.domain.memory import MemorySystem
from src.core.domain.persona import PersonaMask
from src.core.domain.readiness import ActionReadiness
from src.core.domain.resource import ResourceCost
from src.core.domain.stance import Stance
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategy import StrategicMode, StrategicPosture
from src.core.ledger.in_memory_ledger import InMemoryStrategicLedger
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.persistence.in_memory_backend import InMemoryStrategicStateBackend
from src.core.time.frozen_time_source import FrozenTimeSource
from src.execution.domain.execution_job import DlqState, ExecutionJob
from src.execution.queue.execution_queue import InMemoryExecutionQueue
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.memory.store.memory_store import MemoryStore
from src.world.store.world_observation_store import WorldObservationStore


class DummyLifeLoop:
    def suppress_pending_intentions(self, human):
        return


def _human(now: datetime) -> AIHuman:
    human_id = uuid4()
    return AIHuman(
        id=human_id,
        identity=Identity("ops-human", 30, "n/a", "bio", [], [], {}),
        state=BehaviorState(100.0, 100.0, 0.0, now, False),
        memory=MemorySystem([], []),
        stance=Stance({}),
        readiness=ActionReadiness(60.0, 40.0, 80.0),
        intentions=[],
        personas=[
            PersonaMask(
                id=uuid4(),
                human_id=human_id,
                platform="telegram",
                display_name="Ops",
                bio="",
                language="en",
                tone="neutral",
                verbosity="medium",
                activity_rate=1.0,
                risk_tolerance=0.5,
                posting_hours=list(range(24)),
            )
        ],
        strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
        deferred_actions=[],
        created_at=now,
    )


def _intent(now: datetime) -> ExecutionIntent:
    return ExecutionIntent(
        id=uuid4(),
        commitment_id=uuid4(),
        intention_id=uuid4(),
        persona_id=uuid4(),
        abstract_action="communicate",
        constraints={"platform": "telegram", "target_id": "chat-1", "text": "hello"},
        created_at=now,
        reversible=False,
        risk_level=0.1,
        estimated_cost=ResourceCost(1.0, 1.0, 1),
    )


def _service(now: datetime):
    queue = InMemoryExecutionQueue()
    orchestrator = StrategicOrchestrator(
        time_source=FrozenTimeSource(now),
        ledger=InMemoryStrategicLedger(),
        backend=InMemoryStrategicStateBackend(),
        execution_queue=queue,
    )
    context = StrategicContext("global", None, None, "telegram:chat-1")
    orchestrator._runtimes[str(context)] = StrategicContextRuntime(
        context=context,
        lifeloop=DummyLifeLoop(),
        human=_human(now),
        tick_count=7,
        starvation_score=1.5,
        last_win_tick=5,
    )
    service = AdminControlPlaneService(
        orchestrator=orchestrator,
        execution_queue=queue,
        world_store=WorldObservationStore(),
        memory_store=MemoryStore(),
        counterfactual_store=CounterfactualMemoryStore(),
    )
    return service, queue, context


def test_control_plane_lists_contexts_with_runtime_and_queue_stats():
    now = datetime(2025, 1, 10, tzinfo=timezone.utc)
    service, queue, context = _service(now)
    queue.enqueue(ExecutionJob.new(_intent(now), context.domain, {}))

    items = service.list_contexts()
    assert len(items) == 1
    assert items[0]["context_domain"] == context.domain
    assert items[0]["tick_count"] == 7
    assert items[0]["queue_depth"] == 1


def test_control_plane_dlq_replay_is_versioned_and_audited():
    now = datetime(2025, 1, 11, tzinfo=timezone.utc)
    service, queue, context = _service(now)
    intent = _intent(now)
    job_id = queue.enqueue(ExecutionJob.new(intent, context.domain, {}))
    leased = queue.lease("w1", 1, timedelta(seconds=30))
    assert len(leased) == 1
    assert queue.move_to_dlq(job_id, "w1", DlqState.AWAITING_MANUAL_ACTION, "manual")

    replay = service.replay_dlq(job_id, actor="operator-1", role="operator")
    assert replay is not None
    assert replay["job_version"] == 2
    assert replay["parent_job_id"] == str(job_id)

    audit = service.get_mutation_audit(limit=10)
    assert len(audit) == 1
    assert audit[0].action == "dlq_replay"
    assert audit[0].actor == "operator-1"


def test_control_plane_panic_mode_updates_orchestrator_runtime_state():
    now = datetime(2025, 1, 12, tzinfo=timezone.utc)
    service, _, _ = _service(now)

    service.set_panic_mode(enabled=True, actor="admin-1", role="admin")
    assert service.orchestrator._panic_mode is True
    assert "telegram" in service.orchestrator._disabled_platforms

    service.set_panic_mode(enabled=False, actor="admin-1", role="admin")
    assert service.orchestrator._panic_mode is False
    assert "telegram" not in service.orchestrator._disabled_platforms
