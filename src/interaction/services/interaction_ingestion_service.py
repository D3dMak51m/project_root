from src.interaction.domain.interaction_event import InteractionEvent
from src.world.domain.world_observation import WorldObservation
from src.world.services.world_observation_ingestion import WorldObservationIngestionService
from src.world.context.context_buffer import ContextBuffer


class InteractionIngestionService:
    """
    Ingests interaction events into the World Memory and Context Buffer.
    Does NOT trigger reactions.
    """

    def __init__(
            self,
            ingestion_service: WorldObservationIngestionService,
            context_buffer: ContextBuffer
    ):
        self.ingestion_service = ingestion_service
        self.context_buffer = context_buffer

    def ingest(self, event: InteractionEvent) -> None:
        # Create WorldObservation from InteractionEvent
        # Salience/Trends/Targets are optional or calculated later in pipeline if needed.
        # For raw ingestion, we wrap the event.
        observation = WorldObservation(
            interaction=event,
            signal=None,
            salience=None,
            trends=[],
            targets=None
        )

        # 1. Persist to World Memory
        self.ingestion_service.ingest(observation)

        # 2. Add to Context Buffer for next tick
        self.context_buffer.add(observation)