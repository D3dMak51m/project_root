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

        NOTE: The base CounterfactualMemoryStore does not expose a public method to clear or replace events.
        Directly accessing private fields (e.g., _events) violates architectural boundaries.
        Therefore, this implementation cannot be completed without extending the base store contract.

        Per architectural constraints (M11 FIX), we must raise NotImplementedError rather than violate encapsulation.
        """
        raise NotImplementedError(
            "Atomic replacement requires explicit public contract on CounterfactualMemoryStore. "
            "Base store does not support clear/replace operations."
        )