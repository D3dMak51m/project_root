from typing import List
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.memory.interfaces.consolidatable_counterfactual_store import ConsolidatableCounterfactualStore
from src.memory.domain.counterfactual_event import CounterfactualEvent

class ConsolidatableCounterfactualStoreImpl(CounterfactualMemoryStore, ConsolidatableCounterfactualStore):
    """
    Opt-in implementation of CounterfactualMemoryStore that supports atomic consolidation.
    Extends the base store to add replace_all capability.
    """

    def list_all(self) -> List[CounterfactualEvent]:
        """
        Retrieve all counterfactual events. Inherited behavior, explicit for interface compliance.
        """
        return super().list_all()

    def replace_all(self, events: List[CounterfactualEvent]) -> None:
        """
        Atomically replace the entire counterfactual history.
        Uses public API of the base store.
        """
        self.clear()
        self.extend(events)