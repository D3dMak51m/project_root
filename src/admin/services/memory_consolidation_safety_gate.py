from dataclasses import dataclass, field
from typing import List, Union
from src.memory.interfaces.consolidatable_memory_store import ConsolidatableMemoryStore
from src.memory.interfaces.consolidatable_counterfactual_store import ConsolidatableCounterfactualStore
from src.memory.domain.memory_consolidation_context import MemoryConsolidationContext


@dataclass(frozen=True)
class ConsolidationSafetyVerdict:
    """
    Immutable verdict indicating whether consolidation is safe to proceed.
    """
    allowed: bool
    reasons: List[str] = field(default_factory=list)


class MemoryConsolidationSafetyGate:
    """
    Admin-facing service for validating consolidation preconditions.
    Strictly read-only: checks safety rules without executing consolidation.
    """

    def check_safety(
            self,
            store: Union[ConsolidatableMemoryStore, ConsolidatableCounterfactualStore],
            context: MemoryConsolidationContext
    ) -> ConsolidationSafetyVerdict:
        """
        Validates preconditions for memory consolidation.
        Returns a verdict with reasons.
        """
        reasons = []

        # 1. Check if store is empty
        # list_all is read-only
        events = store.list_all()
        if not events:
            reasons.append("Store is empty; consolidation not applicable.")

        # 2. Check policy caps
        policy = context.policy
        if policy.max_events_per_context <= 0:
            reasons.append("Policy max_events_per_context must be positive.")

        if policy.max_counterfactuals_per_context <= 0:
            reasons.append("Policy max_counterfactuals_per_context must be positive.")

        # 3. Check context time validity
        # Basic check: time must be set (dataclass ensures type, but we check for None if optional, though it's not optional in definition)
        if context.current_time is None:
            reasons.append("Context current_time is missing.")

        # Determine final verdict
        allowed = len(reasons) == 0

        return ConsolidationSafetyVerdict(
            allowed=allowed,
            reasons=reasons
        )