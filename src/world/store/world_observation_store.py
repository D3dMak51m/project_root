from typing import List
from src.world.domain.world_observation import WorldObservation

class WorldObservationStore:
    """
    Append-only storage for world observations (signals and interactions).
    Acts as the memory of "what happened in the world".
    """
    def __init__(self):
        self._observations: List[WorldObservation] = []

    def append(self, observation: WorldObservation) -> None:
        self._observations.append(observation)

    def list_all(self) -> List[WorldObservation]:
        return list(self._observations)