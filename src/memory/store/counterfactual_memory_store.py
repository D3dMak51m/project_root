from typing import List
from src.memory.domain.counterfactual_event import CounterfactualEvent


class CounterfactualMemoryStore:
    """
    Append-only in-memory storage for CounterfactualEvents.
    Separate from the main MemoryStore to avoid polluting factual history.
    """

    def __init__(self):
        self._events: List[CounterfactualEvent] = []

    def append(self, event: CounterfactualEvent) -> None:
        self._events.append(event)

    def list_all(self) -> List[CounterfactualEvent]:
        return list(self._events)

    def list_by_context(self, context_domain: str) -> List[CounterfactualEvent]:
        return [e for e in self._events if e.context_domain == context_domain]