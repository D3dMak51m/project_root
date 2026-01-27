from src.core.domain.execution_intent import ExecutionIntent
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime


class StrategicPriorityService:
    """
    Pure service. Calculates dynamic priority for execution intents.
    Balances risk, cost, and context starvation to prevent resource monopolies.
    """

    def compute_priority(
            self,
            intent: ExecutionIntent,
            runtime: StrategicContextRuntime
    ) -> float:
        """
        Calculates the final priority score for arbitration.
        """
        # Base priority from intent risk (higher risk often implies higher urgency/importance in this model)
        # In a full model, intent would have an explicit 'importance' field.
        # Here we use risk_level as a proxy for 'intensity'.
        base_score = intent.risk_level * 10.0

        # Starvation Bonus
        # Contexts that haven't won recently get a boost.
        starvation_bonus = runtime.starvation_score * 2.0

        # Cost Penalty (optional, maybe cheaper actions are preferred?)
        # For now, we don't penalize cost directly in priority,
        # as feasibility is already checked.

        return base_score + starvation_bonus

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
            # Reset or significantly reduce starvation on win
            return 0.0

        if has_intent:
            # If context wanted to act but lost, increase starvation
            # Cap at some reasonable limit (e.g., 10.0)
            return min(10.0, runtime.starvation_score + 1.0)

        # If context didn't want to act, decay starvation slowly
        return max(0.0, runtime.starvation_score - 0.1)