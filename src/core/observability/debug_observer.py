from src.core.observability.strategic_observer import StrategicObserver
from src.core.ledger.strategic_event import StrategicEvent

class DebugStrategicObserver(StrategicObserver):
    """
    Observer that prints events to stdout for development.
    """
    def on_event(self, event: StrategicEvent) -> None:
        print(f"[STRATEGY] {event.timestamp.isoformat()} | {event.event_type} | {event.details}")