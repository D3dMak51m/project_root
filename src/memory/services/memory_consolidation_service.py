from src.memory.interfaces.consolidatable_memory_store import ConsolidatableMemoryStore
from src.memory.interfaces.consolidatable_counterfactual_store import ConsolidatableCounterfactualStore
from src.memory.services.memory_consolidator import MemoryConsolidator
from src.memory.services.counterfactual_consolidator import CounterfactualConsolidator
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext


class MemoryConsolidationService:
    """
    Boundary service for executing memory consolidation.
    Orchestrates the fetch-consolidate-replace cycle for memory stores.
    Does NOT decide when to run. Does NOT handle errors.
    """

    def consolidate_events(
            self,
            store: ConsolidatableMemoryStore,
            consolidator: MemoryConsolidator,
            context: MemoryConsolidationContext
    ) -> None:
        """
        Executes consolidation for the main event memory store.
        """
        # 1. Fetch all events
        events = store.list_all()

        # 2. Apply consolidation logic (pure)
        consolidated_events = consolidator.consolidate(events, context)

        # 3. Atomically replace store content
        store.replace_all(consolidated_events)

    def consolidate_counterfactuals(
            self,
            store: ConsolidatableCounterfactualStore,
            consolidator: CounterfactualConsolidator,
            context: MemoryConsolidationContext
    ) -> None:
        """
        Executes consolidation for the counterfactual memory store.
        """
        # 1. Fetch all events
        events = store.list_all()

        # 2. Apply consolidation logic (pure)
        consolidated_events = consolidator.consolidate(events, context)

        # 3. Atomically replace store content
        store.replace_all(consolidated_events)