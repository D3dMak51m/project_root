from src.world.domain.world_observation import WorldObservation
from src.world.store.world_observation_store import WorldObservationStore
from src.core.observability.strategic_observer import StrategicObserver
from src.core.observability.telemetry_event import TelemetryEvent
from datetime import datetime, timezone


class WorldObservationIngestionService:
    """
    Service for persisting world observations and notifying telemetry.
    """

    def __init__(self, store: WorldObservationStore, observer: StrategicObserver):
        self.store = store
        self.observer = observer

    def ingest(self, observation: WorldObservation) -> None:
        self.store.append(observation)

        # Telemetry Hook
        source = "unknown"
        if observation.signal:
            source = observation.signal.source_id
        elif observation.interaction:
            source = f"{observation.interaction.platform}:{observation.interaction.user_id}"

        self.observer.on_telemetry(TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="WORLD_OBSERVATION_ADDED",
            source_component="WorldIngestion",
            payload={"source": source, "context_domain": observation.context_domain}
        ))
