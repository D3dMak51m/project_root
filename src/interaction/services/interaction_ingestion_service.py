from typing import Callable, Optional

from src.core.domain.entity import AIHuman
from src.core.domain.strategic_context import StrategicContext
from src.interaction.domain.interaction_event import InteractionEvent
from src.world.domain.world_observation import WorldObservation
from src.world.services.world_observation_ingestion import WorldObservationIngestionService
from src.world.context.context_buffer import ContextBuffer
from src.infrastructure.services.dialogue_context_resolver import DialogueContextResolver


class InteractionIngestionService:
    """
    Ingests interaction events into the World Memory and Context Buffer.
    Does NOT trigger reactions.
    """

    def __init__(
            self,
            ingestion_service: WorldObservationIngestionService,
            context_buffer: ContextBuffer,
            dialogue_context_resolver: Optional[DialogueContextResolver] = None,
            orchestrator=None,
            default_human: Optional[AIHuman] = None,
            human_resolver: Optional[Callable[[InteractionEvent, StrategicContext], Optional[AIHuman]]] = None
    ):
        self.ingestion_service = ingestion_service
        self.context_buffer = context_buffer
        self.dialogue_context_resolver = dialogue_context_resolver
        self.orchestrator = orchestrator
        self.default_human = default_human
        self.human_resolver = human_resolver

    def ingest(self, event: InteractionEvent) -> None:
        strategic_context = self._resolve_context(event)

        if strategic_context and self.orchestrator:
            human = self._resolve_human(event, strategic_context)
            if human:
                self.orchestrator.register_context(strategic_context, human)

        # Create WorldObservation from InteractionEvent
        # Salience/Trends/Targets are optional or calculated later in pipeline if needed.
        # For raw ingestion, we wrap the event.
        observation = WorldObservation(
            interaction=event,
            signal=None,
            salience=None,
            trends=[],
            targets=None,
            context_domain=strategic_context.domain if strategic_context else None
        )

        # 1. Persist to World Memory
        self.ingestion_service.ingest(observation)

        # 2. Add to Context Buffer for next tick
        self.context_buffer.add(observation)

    def _resolve_context(self, event: InteractionEvent) -> Optional[StrategicContext]:
        if self.dialogue_context_resolver and event.platform == "telegram":
            return self.dialogue_context_resolver.resolve(event.chat_id)

        context_domain = event.raw_metadata.get("context_domain")
        if not context_domain:
            return None

        return StrategicContext(
            country="global",
            region=None,
            goal_id=None,
            domain=context_domain
        )

    def _resolve_human(self, event: InteractionEvent, context: StrategicContext) -> Optional[AIHuman]:
        if self.human_resolver:
            return self.human_resolver(event, context)
        return self.default_human
