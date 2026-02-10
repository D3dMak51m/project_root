from src.memory.interfaces.consolidatable_memory_store import ConsolidatableMemoryStore
from src.memory.interfaces.consolidatable_counterfactual_store import ConsolidatableCounterfactualStore
from src.memory.services.memory_consolidator import MemoryConsolidator
from src.memory.services.counterfactual_consolidator import CounterfactualConsolidator
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext
from src.memory.services.memory_consolidation_service import MemoryConsolidationService

class MemoryConsolidationAdminService:
    """
    Admin-facing service for triggering manual memory consolidation.
    This service acts as a bridge between administrative commands and the core consolidation logic.
    It does NOT contain any scheduling or automatic triggering logic.
    """

    def __init__(self, consolidation_service: MemoryConsolidationService):
        self.consolidation_service = consolidation_service

    def consolidate_events(
        self,
        store: ConsolidatableMemoryStore,
        consolidator: MemoryConsolidator,
        context: MemoryConsolidationContext
    ) -> None:
        """
        Manually trigger consolidation for the event memory store.
        Requires explicit store, consolidator, and context.
        """
        self.consolidation_service.consolidate_events(store, consolidator, context)

    def consolidate_counterfactuals(
        self,
        store: ConsolidatableCounterfactualStore,
        consolidator: CounterfactualConsolidator,
        context: MemoryConsolidationContext
    ) -> None:
        """
        Manually trigger consolidation for the counterfactual memory store.
        Requires explicit store, consolidator, and context.
        """
        self.consolidation_service.consolidate_counterfactuals(store, consolidator, context)