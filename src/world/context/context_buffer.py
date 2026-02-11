from typing import List
from src.world.domain.world_observation import WorldObservation

class ContextBuffer:
    """
    Transient buffer for incoming world observations that haven't been processed by LifeLoop yet.
    Decouples ingestion from processing.
    """
    def __init__(self):
        self._buffer: List[WorldObservation] = []

    def add(self, observation: WorldObservation) -> None:
        self._buffer.append(observation)

    def pop_all(self) -> List[WorldObservation]:
        """
        Retrieves and clears the buffer.
        Called by Orchestrator at the start of a tick.
        """
        items = list(self._buffer)
        self._buffer.clear()
        return items