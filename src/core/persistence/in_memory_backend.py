from typing import Dict, Optional
from src.core.domain.strategic_context import StrategicContext
from src.core.persistence.strategic_state_backend import StrategicStateBackend
from src.core.persistence.strategic_state_bundle import StrategicStateBundle

class InMemoryStrategicStateBackend(StrategicStateBackend):
    """
    Simple in-memory implementation for testing and development.
    Not suitable for production persistence across process restarts.
    """
    def __init__(self):
        self._store: Dict[str, StrategicStateBundle] = {}

    def load(self, context: StrategicContext) -> Optional[StrategicStateBundle]:
        key = str(context)
        return self._store.get(key)

    def save(self, context: StrategicContext, bundle: StrategicStateBundle) -> None:
        key = str(context)
        self._store[key] = bundle