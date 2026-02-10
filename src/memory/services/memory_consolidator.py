from typing import List
from src.memory.domain.event_record import EventRecord
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext, ConsolidationMode
from src.core.domain.execution_result import ExecutionStatus


class MemoryConsolidator:
    """
    Pure service. Consolidates event memory based on policy and context.
    Returns a new list of retained events.
    """

    def consolidate(
            self,
            events: List[EventRecord],
            context: MemoryConsolidationContext
    ) -> List[EventRecord]:

        if context.mode == ConsolidationMode.OFF:
            return list(events)

        policy = context.policy

        # 1. Sort by time (ensure deterministic order)
        sorted_events = sorted(events, key=lambda e: e.issued_at)

        # 2. Filter by Age (if applicable)
        # For M.8, we focus on count limits and relevance, but age check is valid.
        # We keep it simple: retain based on count and type priority.

        retained = []
        failures = []
        successes = []
        others = []

        for event in sorted_events:
            if event.execution_status in (ExecutionStatus.FAILED, ExecutionStatus.REJECTED):
                failures.append(event)
            elif event.execution_status == ExecutionStatus.SUCCESS:
                successes.append(event)
            else:
                others.append(event)

        # 3. Apply Retention Rules

        # Failures: Keep last N
        failures_to_keep = failures[-policy.retain_last_n_failures:]

        # Successes: Keep all if policy says so, else cap
        # If aggressive, cap successes too
        if context.mode == ConsolidationMode.AGGRESSIVE:
            successes_to_keep = successes[-policy.max_events_per_context // 2:]
        else:
            successes_to_keep = successes if policy.retain_successful_events else successes[-100:]

        # Others: Keep recent
        others_to_keep = others[-100:]

        # 4. Merge and Sort
        merged = failures_to_keep + successes_to_keep + others_to_keep
        merged.sort(key=lambda e: e.issued_at)

        # 5. Global Cap
        if len(merged) > policy.max_events_per_context:
            # Drop oldest, but try to preserve recent failures/successes priority?
            # Simple cap from end (keep most recent)
            merged = merged[-policy.max_events_per_context:]

        return merged