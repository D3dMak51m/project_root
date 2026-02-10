from typing import List
from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext, ConsolidationMode


class CounterfactualConsolidator:
    """
    Pure service. Consolidates counterfactual memory.
    """

    def consolidate(
            self,
            events: List[CounterfactualEvent],
            context: MemoryConsolidationContext
    ) -> List[CounterfactualEvent]:

        if context.mode == ConsolidationMode.OFF:
            return list(events)

        if not context.policy.retain_counterfactuals:
            return []

        policy = context.policy

        # 1. Sort
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # 2. Apply Cap
        # Counterfactuals are less critical than execution events, so we just cap by count/age.
        # We prioritize recent ones.

        limit = policy.max_counterfactuals_per_context
        if context.mode == ConsolidationMode.AGGRESSIVE:
            limit = limit // 2

        if len(sorted_events) > limit:
            return sorted_events[-limit:]

        return sorted_events