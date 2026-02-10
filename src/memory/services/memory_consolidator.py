from typing import List
from src.memory.domain.event_record import EventRecord
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext


class MemoryConsolidator:
    """
    Pure service. Consolidates event memory based on policy limits.
    Strictly quantitative: enforces max count and time order.
    Does NOT interpret event semantics (success/failure).
    """

    def consolidate(
            self,
            events: List[EventRecord],
            context: MemoryConsolidationContext
    ) -> List[EventRecord]:
        policy = context.policy

        # 1. Sort by time (ensure deterministic order)
        sorted_events = sorted(events, key=lambda e: e.issued_at)

        # 2. Apply Global Cap
        # Simple truncation from the beginning (keep most recent)
        if len(sorted_events) > policy.max_events_per_context:
            return sorted_events[-policy.max_events_per_context:]

        return sorted_events