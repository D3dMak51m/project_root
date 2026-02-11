from src.interaction.domain.interaction_event import InteractionEvent
from src.core.observability.strategic_observer import StrategicObserver
from src.core.observability.telemetry_event import TelemetryEvent
from datetime import datetime, timezone

class InteractionAutonomyBridge:
    """
    Bridges inbound interactions to the Autonomy layer via Telemetry.
    NO LONGER triggers ticks directly.
    """
    def __init__(self, observer: StrategicObserver):
        self.observer = observer

    def process_interaction(self, event: InteractionEvent) -> None:
        # Telemetry Hook only
        self.observer.on_telemetry(TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="INBOUND_INTERACTION",
            source_component="InteractionBridge",
            payload={
                "platform": event.platform,
                "user_id": event.user_id,
                "type": event.message_type
            }
        ))