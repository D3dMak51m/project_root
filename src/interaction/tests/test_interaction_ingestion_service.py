from datetime import datetime, timezone
from uuid import uuid4

from src.core.domain.behavior import BehaviorState
from src.core.domain.entity import AIHuman
from src.core.domain.identity import Identity
from src.core.domain.memory import MemorySystem
from src.core.domain.readiness import ActionReadiness
from src.core.domain.stance import Stance
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.infrastructure.services.dialogue_context_resolver import DialogueContextResolver
from src.interaction.domain.interaction_event import InteractionEvent
from src.interaction.services.interaction_ingestion_service import InteractionIngestionService
from src.world.context.context_buffer import ContextBuffer


class RecordingWorldIngestion:
    def __init__(self):
        self.observations = []

    def ingest(self, observation):
        self.observations.append(observation)


class RecordingOrchestrator:
    def __init__(self):
        self.registrations = []

    def register_context(self, context, human):
        self.registrations.append((context, human))


def _create_human(now: datetime) -> AIHuman:
    return AIHuman(
        id=uuid4(),
        identity=Identity("ingest-human", 30, "n/a", "bio", [], [], {}),
        state=BehaviorState(100.0, 100.0, 0.0, now, False),
        memory=MemorySystem([], []),
        stance=Stance({}),
        readiness=ActionReadiness(50.0, 40.0, 80.0),
        intentions=[],
        personas=[],
        strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
        deferred_actions=[],
        created_at=now
    )


def test_ingestion_resolves_dialogue_context_and_registers_runtime_context():
    now = datetime(2025, 1, 3, tzinfo=timezone.utc)
    event = InteractionEvent(
        id=uuid4(),
        platform="telegram",
        user_id="user-1",
        chat_id="123",
        content="hello",
        message_type="text",
        timestamp=now,
        raw_metadata={}
    )

    ingestion_backend = RecordingWorldIngestion()
    orchestrator = RecordingOrchestrator()
    human = _create_human(now)
    buffer = ContextBuffer()

    service = InteractionIngestionService(
        ingestion_service=ingestion_backend,
        context_buffer=buffer,
        dialogue_context_resolver=DialogueContextResolver(),
        orchestrator=orchestrator,
        default_human=human
    )
    service.ingest(event)

    assert len(orchestrator.registrations) == 1
    registered_context, registered_human = orchestrator.registrations[0]
    assert registered_context.domain == "telegram:123"
    assert registered_human.id == human.id

    assert len(ingestion_backend.observations) == 1
    assert ingestion_backend.observations[0].context_domain == "telegram:123"

    buffered = buffer.pop_all()
    assert len(buffered) == 1
    assert buffered[0].context_domain == "telegram:123"


def test_ingestion_supports_context_domain_from_metadata_without_resolver():
    now = datetime(2025, 1, 4, tzinfo=timezone.utc)
    event = InteractionEvent(
        id=uuid4(),
        platform="web",
        user_id="user-2",
        chat_id="ignored",
        content="hello",
        message_type="text",
        timestamp=now,
        raw_metadata={"context_domain": "web:room-7"}
    )

    ingestion_backend = RecordingWorldIngestion()
    buffer = ContextBuffer()

    service = InteractionIngestionService(
        ingestion_service=ingestion_backend,
        context_buffer=buffer
    )
    service.ingest(event)

    assert len(ingestion_backend.observations) == 1
    assert ingestion_backend.observations[0].context_domain == "web:room-7"
