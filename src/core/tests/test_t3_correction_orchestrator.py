from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.core.context.internal import InternalContext
from src.core.domain.behavior import BehaviorState
from src.core.domain.entity import AIHuman
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.core.domain.identity import Identity
from src.core.domain.memory import MemorySystem
from src.core.domain.persona import PersonaMask
from src.core.domain.readiness import ActionReadiness
from src.core.domain.resource import ResourceCost
from src.core.domain.stance import Stance
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.ledger.budget_event import BudgetEvent
from src.core.ledger.in_memory_ledger import InMemoryStrategicLedger
from src.core.ledger.strategic_event import StrategicEvent
from src.core.lifecycle.signals import LifeSignals
from src.core.observability.strategic_observer import StrategicObserver
from src.core.observability.telemetry_event import TelemetryEvent
from src.core.orchestration.routing_policy import ContextRoutingPolicy
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.persistence.in_memory_backend import InMemoryStrategicStateBackend
from src.core.time.frozen_time_source import FrozenTimeSource
from src.infrastructure.services.telegram_persona_projection import TelegramPersonaProjectionService
from src.integration.registry import ExecutionAdapterRegistry
from src.world.domain.world_observation import WorldObservation
from src.interaction.domain.interaction_event import InteractionEvent
from src.execution.queue.execution_queue import InMemoryExecutionQueue


class RecordingObserver(StrategicObserver):
    def __init__(self):
        self.telemetry = []
        self.execution_results = []

    def on_strategic_event(self, event: StrategicEvent, is_replay: bool = False) -> None:
        return

    def on_budget_event(self, event: BudgetEvent, is_replay: bool = False) -> None:
        return

    def on_execution_result(self, result: ExecutionResult, is_replay: bool = False) -> None:
        self.execution_results.append(result)

    def on_telemetry(self, event: TelemetryEvent) -> None:
        self.telemetry.append(event)


class RecordingRoutingPolicy(ContextRoutingPolicy):
    def __init__(self, contexts):
        self.contexts = contexts

    def resolve(self, signals: LifeSignals, available_contexts):
        return [c for c in self.contexts if c in available_contexts]


class RecordingLifeLoop:
    def __init__(self, intent=None):
        self.intent = intent
        self.last_memories = None
        self.last_human = None

    def tick(self, human, signals, strategic_context, tick_count, last_executed_intent=None):
        self.last_memories = list(signals.memories)
        self.last_human = human
        return InternalContext(
            identity_summary="test",
            current_mood="neutral",
            energy_level="high",
            recent_thoughts=[],
            active_intentions_count=0,
            readiness_level="ready",
            readiness_value=100.0,
            world_perception=None,
            execution_intent=self.intent
        )

    def suppress_pending_intentions(self, human) -> None:
        return


class RecordingTelegramAdapter:
    def __init__(self):
        self.received_intents = []

    def execute(self, intent):
        self.received_intents.append(intent)
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(timezone.utc),
            effects=["message_sent"],
            observations={"message_id": 777},
            failure_type=ExecutionFailureType.NONE
        )


class RecordingPersonaProjectionService(TelegramPersonaProjectionService):
    def __init__(self):
        self.calls = []

    def project(self, intent, mask):
        self.calls.append((intent, mask))
        return super().project(intent, mask)


def _create_human(now: datetime, platform: str = "telegram") -> AIHuman:
    human_id = uuid4()
    return AIHuman(
        id=human_id,
        identity=Identity("test-human", 30, "n/a", "bio", [], [], {}),
        state=BehaviorState(100.0, 100.0, 0.0, now, False),
        memory=MemorySystem([], []),
        stance=Stance({}),
        readiness=ActionReadiness(60.0, 40.0, 80.0),
        intentions=[],
        personas=[
            PersonaMask(
                id=uuid4(),
                human_id=human_id,
                platform=platform,
                display_name="Persona",
                bio="",
                language="en",
                tone="formal",
                verbosity="medium",
                activity_rate=1.0,
                risk_tolerance=0.5,
                posting_hours=list(range(24))
            )
        ],
        strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
        deferred_actions=[],
        created_at=now
    )


def _create_signals():
    return LifeSignals(
        pressure_delta=0.0,
        energy_delta=0.0,
        attention_delta=0.0,
        rest=False,
        perceived_topics={},
        memories=[],
        execution_feedback=None
    )


def test_persona_projection_runs_inside_orchestrator_before_execution():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    context = StrategicContext("global", None, None, "telegram:chat-1")
    human = _create_human(now, platform="telegram")
    observer = RecordingObserver()
    projection = RecordingPersonaProjectionService()

    intent = ExecutionIntent(
        id=uuid4(),
        commitment_id=uuid4(),
        intention_id=uuid4(),
        persona_id=human.personas[0].id,
        abstract_action="communicate",
        constraints={
            "platform": "telegram",
            "target_id": "chat-1",
            "text": "<b>unsafe & text</b>"
        },
        created_at=now,
        reversible=False,
        risk_level=0.1,
        estimated_cost=ResourceCost(1.0, 1.0, 1)
    )

    lifeloop = RecordingLifeLoop(intent=intent)

    registry = ExecutionAdapterRegistry()
    queue = InMemoryExecutionQueue()

    orchestrator = StrategicOrchestrator(
        time_source=FrozenTimeSource(now),
        ledger=InMemoryStrategicLedger(),
        backend=InMemoryStrategicStateBackend(),
        routing_policy=RecordingRoutingPolicy([context]),
        adapter_registry=registry,
        observer=observer,
        persona_projection_service=projection,
        execution_queue=queue,
    )
    orchestrator._runtimes[str(context)] = StrategicContextRuntime(
        context=context,
        lifeloop=lifeloop,
        human=human
    )

    winner = orchestrator.tick(human, _create_signals())

    assert winner is not None
    assert len(projection.calls) == 1
    assert queue.depth() == 1

    leased = queue.lease("test-worker", 1, timedelta(seconds=30))
    assert len(leased) == 1
    executed = leased[0].intent
    assert executed.constraints["text"] == "&lt;b&gt;unsafe &amp; text&lt;/b&gt;"
    assert executed.constraints["parse_mode"] == "HTML"
    assert executed.constraints["platform"] == "telegram"

    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        timestamp=now,
        effects=["message_sent"],
        observations={"message_id": 777},
        failure_type=ExecutionFailureType.NONE
    )
    orchestrator.post_execution_pipeline(
        {
            "intent_id": executed.id,
            "intent": executed,
            "context_domain": context.domain,
            "reservation_delta": leased[0].reservation_delta,
            "result": result,
        }
    )

    sent_events = [e for e in observer.telemetry if e.event_type == "TELEGRAM_MESSAGE_SENT"]
    assert len(sent_events) == 1
    assert sent_events[0].context_id == context.domain


def test_buffer_observations_are_scoped_by_context_domain_and_runtime_human():
    now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    context_a = StrategicContext("global", None, None, "telegram:chat-a")
    context_b = StrategicContext("global", None, None, "telegram:chat-b")
    fallback_human = _create_human(now, platform="dev")
    human_a = _create_human(now, platform="telegram")
    human_b = _create_human(now, platform="telegram")

    loop_a = RecordingLifeLoop(intent=None)
    loop_b = RecordingLifeLoop(intent=None)

    orchestrator = StrategicOrchestrator(
        time_source=FrozenTimeSource(now),
        ledger=InMemoryStrategicLedger(),
        backend=InMemoryStrategicStateBackend(),
        routing_policy=RecordingRoutingPolicy([context_a, context_b]),
        adapter_registry=ExecutionAdapterRegistry(),
        observer=RecordingObserver()
    )
    orchestrator._runtimes[str(context_a)] = StrategicContextRuntime(
        context=context_a,
        lifeloop=loop_a,
        human=human_a
    )
    orchestrator._runtimes[str(context_b)] = StrategicContextRuntime(
        context=context_b,
        lifeloop=loop_b,
        human=human_b
    )

    interaction_a = InteractionEvent(
        id=uuid4(),
        platform="telegram",
        user_id="user-a",
        chat_id="chat-a",
        content="hello-a",
        message_type="text",
        timestamp=now,
        raw_metadata={}
    )
    interaction_b = InteractionEvent(
        id=uuid4(),
        platform="telegram",
        user_id="user-b",
        chat_id="chat-b",
        content="hello-b",
        message_type="text",
        timestamp=now,
        raw_metadata={}
    )

    orchestrator.context_buffer.add(WorldObservation(interaction=interaction_a, context_domain=context_a.domain))
    orchestrator.context_buffer.add(WorldObservation(interaction=interaction_b, context_domain=context_b.domain))

    orchestrator.tick(fallback_human, _create_signals())

    assert any("user-a" in m for m in loop_a.last_memories)
    assert all("user-b" not in m for m in loop_a.last_memories)
    assert any("user-b" in m for m in loop_b.last_memories)
    assert all("user-a" not in m for m in loop_b.last_memories)
    assert loop_a.last_human.id == human_a.id
    assert loop_b.last_human.id == human_b.id
