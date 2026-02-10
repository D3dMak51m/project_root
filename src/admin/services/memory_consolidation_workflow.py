from typing import List, Tuple, Union
from src.memory.interfaces.consolidatable_memory_store import ConsolidatableMemoryStore
from src.memory.interfaces.consolidatable_counterfactual_store import ConsolidatableCounterfactualStore
from src.memory.services.memory_consolidator import MemoryConsolidator
from src.memory.services.counterfactual_consolidator import CounterfactualConsolidator
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext
from src.memory.domain.event_record import EventRecord
from src.memory.domain.counterfactual_event import CounterfactualEvent

from src.admin.services.memory_consolidation_safety_gate import MemoryConsolidationSafetyGate, ConsolidationSafetyVerdict
from src.admin.services.memory_consolidation_preview_service import MemoryConsolidationPreviewService
from src.admin.services.memory_consolidation_admin_service import MemoryConsolidationAdminService

class MemoryConsolidationWorkflow:
    """
    Admin-facing workflow for memory consolidation.
    Composes safety checks, previews, and execution into explicit, manual steps.
    Does NOT automate or schedule consolidation.
    """

    def __init__(
        self,
        safety_gate: MemoryConsolidationSafetyGate,
        preview_service: MemoryConsolidationPreviewService,
        admin_service: MemoryConsolidationAdminService
    ):
        self.safety_gate = safety_gate
        self.preview_service = preview_service
        self.admin_service = admin_service

    def check_safety(
        self,
        store: Union[ConsolidatableMemoryStore, ConsolidatableCounterfactualStore],
        context: MemoryConsolidationContext
    ) -> ConsolidationSafetyVerdict:
        """
        Step 1: Check if consolidation is safe/applicable.
        Read-only.
        """
        return self.safety_gate.check_safety(store, context)

    def preview_events(
        self,
        store: ConsolidatableMemoryStore,
        consolidator: MemoryConsolidator,
        context: MemoryConsolidationContext
    ) -> Tuple[List[EventRecord], List[EventRecord]]:
        """
        Step 2 (Optional): Preview event consolidation results.
        Read-only.
        """
        return self.preview_service.preview_events(store, consolidator, context)

    def preview_counterfactuals(
        self,
        store: ConsolidatableCounterfactualStore,
        consolidator: CounterfactualConsolidator,
        context: MemoryConsolidationContext
    ) -> Tuple[List[CounterfactualEvent], List[CounterfactualEvent]]:
        """
        Step 2 (Optional): Preview counterfactual consolidation results.
        Read-only.
        """
        return self.preview_service.preview_counterfactuals(store, consolidator, context)

    def execute_events(
        self,
        store: ConsolidatableMemoryStore,
        consolidator: MemoryConsolidator,
        context: MemoryConsolidationContext
    ) -> None:
        """
        Step 3 (Explicit): Execute event consolidation.
        Mutates the store.
        """
        self.admin_service.consolidate_events(store, consolidator, context)

    def execute_counterfactuals(
        self,
        store: ConsolidatableCounterfactualStore,
        consolidator: CounterfactualConsolidator,
        context: MemoryConsolidationContext
    ) -> None:
        """
        Step 3 (Explicit): Execute counterfactual consolidation.
        Mutates the store.
        """
        self.admin_service.consolidate_counterfactuals(store, consolidator, context)