from abc import ABC, abstractmethod
from typing import List
from src.core.lifecycle.signals import LifeSignals
from src.core.domain.strategic_context import StrategicContext

class ContextRoutingPolicy(ABC):
    """
    Determines which StrategicContext(s) should receive a given LifeSignals input.
    """
    @abstractmethod
    def resolve(self, signals: LifeSignals, available_contexts: List[StrategicContext]) -> List[StrategicContext]:
        pass

class DefaultRoutingPolicy(ContextRoutingPolicy):
    """
    Default policy:
    - If signals contain execution feedback, route to the context of the originating intent (if traceable).
    - Otherwise, broadcast to all active contexts (simplified for E.6).
    - In a real system, this would analyze signal content/metadata.
    """
    def resolve(self, signals: LifeSignals, available_contexts: List[StrategicContext]) -> List[StrategicContext]:
        # For E.6, we implement a simple broadcast or targeted routing if metadata exists.
        # Assuming signals might carry context info in future, but for now broadcast is safe default
        # as LifeLoop filters relevance via Perception/Internalization layers.
        return available_contexts