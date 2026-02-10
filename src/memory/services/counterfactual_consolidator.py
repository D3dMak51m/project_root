from typing import List
from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext


class CounterfactualConsolidator:
    """
    Pure service. Consolidates counterfactual memory based on policy limits.
    Strictly quantitative.
    """

    def consolidate(
            self,
            events: List[CounterfactualEvent],
            context: MemoryConsolidationContext
    ) -> List[CounterfactualEvent]:

        if not context.policy.retain_counterfactuals:
            return []

        policy = context.policy

        # 1. Sort
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # 2. Apply Cap
        limit = policy.max_counterfactuals_per_context
        if len(sorted_events) > limit:
            return sorted_events[-limit:]

        return sorted_events