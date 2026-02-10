from typing import List, Tuple
from src.memory.interfaces.consolidatable_memory_store import ConsolidatableMemoryStore
from src.memory.interfaces.consolidatable_counterfactual_store import ConsolidatableCounterfactualStore
from src.memory.services.memory_consolidator import MemoryConsolidator
from src.memory.services.counterfactual_consolidator import CounterfactualConsolidator
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext
from src.memory.domain.event_record import EventRecord
from src.memory.domain.counterfactual_event import CounterfactualEvent


class MemoryConsolidationPreviewService:
    """
    Admin-facing service for previewing memory consolidation results.
    Strictly read-only: calculates what would happen without applying changes.
    """

    def preview_events(
            self,
            store: ConsolidatableMemoryStore,
            consolidator: MemoryConsolidator,
            context: MemoryConsolidationContext
    ) -> Tuple[List[EventRecord], List[EventRecord]]:
        """
        Preview consolidation for event memory.
        Returns (original_events, consolidated_events).
        Does NOT mutate the store.
        """
        # 1. Fetch all events (Read-only)
        original_events = store.list_all()

        # 2. Apply consolidation logic (Pure)
        consolidated_events = consolidator.consolidate(original_events, context)

        # 3. Return comparison data
        return original_events, consolidated_events

    def preview_counterfactuals(
            self,
            store: ConsolidatableCounterfactualStore,
            consolidator: CounterfactualConsolidator,
            context: MemoryConsolidationContext
    ) -> Tuple[List[CounterfactualEvent], List[CounterfactualEvent]]:
        """
        Preview consolidation for counterfactual memory.
        Returns (original_events, consolidated_events).
        Does NOT mutate the store.
        """
        # 1. Fetch all events (Read-only)
        original_events = store.list_all()

        # 2. Apply consolidation logic (Pure)
        consolidated_events = consolidator.consolidate(original_events, context)

        # 3. Return comparison data
        return original_events, consolidated_events