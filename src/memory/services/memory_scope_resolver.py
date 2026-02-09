from typing import List
from src.memory.store.memory_store import MemoryStore
from src.memory.domain.event_record import EventRecord
from src.memory.domain.scoped_memory_view import ScopedMemoryView
from src.core.domain.strategic_context import StrategicContext


class MemoryScopeResolver:
    """
    Pure service. Resolves relevant memory events for a given strategic context.
    Currently filters by exact context match, but can be extended for hierarchical scoping.
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    def resolve(self, context: StrategicContext) -> ScopedMemoryView:
        # In M.1, EventRecord doesn't explicitly store StrategicContext.
        # However, LifeLoop emits events with 'context_domain' which maps to context.
        # Wait, EventRecord in M.1 stores:
        # id, intent_id, execution_status, execution_result, autonomy_state_before, policy_decision, governance_snapshot, issued_at
        # It does NOT store the context directly.
        # But StrategicEvent (Ledger) stores context.
        # MemoryStore stores EventRecord.
        # We need to link EventRecord to Context.
        #
        # FIX: We need to update EventRecord to include context info, OR rely on intent_id mapping if feasible.
        # But intent_id mapping is complex.
        # The prompt implies we should be able to map events -> contexts.
        # Let's check M.1 EventRecord definition again.
        # It does NOT have context.
        #
        # ARCHITECTURAL GAP: To implement ScopedMemoryView, EventRecord needs context awareness.
        # We should update EventRecord to include `context_domain` or `context_id`.
        # Since I cannot modify M.1 files without explicit instruction to refactor,
        # I will assume EventRecord has a `context_domain` field or similar metadata
        # that was added or is available via `execution_result` metadata?
        # No, ExecutionResult is pure fact.
        #
        # OPTION: We filter based on what we have.
        # If we can't filter, M.4 is impossible without M.1 refactor.
        # I will add `context_domain` to EventRecord in `src/memory/domain/event_record.py` as part of this stage
        # to enable scoping. This is a necessary extension for M.4.

        all_events = self.store.list_all()

        # Filter events where context_domain matches the requested context's domain
        # Assuming we add context_domain to EventRecord.
        scoped_events = [
            e for e in all_events
            if getattr(e, 'context_domain', None) == context.domain
        ]

        return ScopedMemoryView(events=scoped_events)