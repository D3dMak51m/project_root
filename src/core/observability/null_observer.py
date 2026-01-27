from src.core.observability.strategic_observer import StrategicObserver
from src.core.ledger.strategic_event import StrategicEvent

class NullStrategicObserver(StrategicObserver):
    """
    Default no-op observer.
    """
    def on_event(self, event: StrategicEvent) -> None:
        pass