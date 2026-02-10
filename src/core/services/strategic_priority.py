from typing import Optional
from src.core.domain.execution_intent import ExecutionIntent
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime
from src.memory.domain.strategic_memory_context import StrategicMemoryContext


class StrategicPriorityService:
    """
    Pure service. Calculates dynamic priority for execution intents.
    Balances risk, cost, context starvation, and MEMORY CONTEXT.
    """

    def compute_priority(
            self,
            intent: ExecutionIntent,
            runtime: StrategicContextRuntime,
            memory_context: Optional[StrategicMemoryContext] = None  # [NEW]
    ) -> float:
        """
        Calculates the final priority score for arbitration.
        """
        # Base priority from intent risk
        base_score = intent.risk_level * 10.0

        # Starvation Bonus
        starvation_bonus = runtime.starvation_score * 2.0

        # Memory Context Modulation [NEW]
        memory_mod = 1.0
        risk_penalty = 0.0

        if memory_context:
            memory_mod = memory_context.priority_modifier

            # Apply risk bias:
            # If bias is negative (averse), penalize high risk intents
            if memory_context.risk_bias < 0:
                risk_penalty = intent.risk_level * abs(memory_context.risk_bias) * 5.0

            # If exploration suppressed and intent is high risk (proxy for exploration), penalize heavily
            if memory_context.exploration_suppressed and intent.risk_level > 0.5:
                risk_penalty += 5.0

        final_score = (base_score + starvation_bonus - risk_penalty) * memory_mod

        return max(0.0, final_score)

    def update_starvation(
            self,
            runtime: StrategicContextRuntime,
            is_winner: bool,
            has_intent: bool
    ) -> float:
        """
        Calculates the new starvation score for a context.
        """
        if is_winner:
            return 0.0

        if has_intent:
            return min(10.0, runtime.starvation_score + 1.0)

        return max(0.0, runtime.starvation_score - 0.1)