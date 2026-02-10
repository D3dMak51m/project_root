from typing import List, Protocol
from src.memory.domain.counterfactual_event import CounterfactualEvent

class ConsolidatableCounterfactualStore(Protocol):
    """
    Contract for counterfactual memory stores that support atomic consolidation.
    """
    def list_all(self) -> List[CounterfactualEvent]:
        """Retrieve all counterfactual events for consolidation analysis."""
        ...

    def replace_all(self, events: List[CounterfactualEvent]) -> None:
        """Atomically replace the entire counterfactual history."""
        ...