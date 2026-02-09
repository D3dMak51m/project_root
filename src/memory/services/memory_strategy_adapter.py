from src.memory.domain.memory_signal import MemorySignal
from src.memory.domain.strategic_memory_context import StrategicMemoryContext


class MemoryStrategyAdapter:
    """
    Pure service. Translates raw MemorySignal into actionable StrategicMemoryContext.
    Now includes counterfactual signals.
    """

    def adapt(self, signal: MemorySignal) -> StrategicMemoryContext:
        # 1. Risk Bias Calculation
        risk_bias = 0.0
        if signal.failure_pressure > 2.0:
            risk_bias = -0.5
        elif signal.failure_pressure > 0.5:
            risk_bias = -0.2

        if signal.recent_success:
            risk_bias += 0.1

        # [NEW] Counterfactual Influence on Risk
        # High friction -> Become more conservative (don't bang head against wall)
        if signal.governance_friction_index > 0.5:
            risk_bias -= 0.3
        # High missed opportunity -> Slight push to risk (FOMO), but capped by friction
        elif signal.missed_opportunity_pressure > 0.5 and signal.governance_friction_index < 0.3:
            risk_bias += 0.2

        risk_bias = max(-1.0, min(1.0, risk_bias))

        # 2. Cooldown Requirement
        cooldown = signal.instability_detected

        # 3. Exploration Suppression
        exploration_suppressed = (
                signal.instability_detected or
                signal.governance_suppressed_ratio > 0.3 or
                signal.policy_conflict_density > 0.4  # [NEW] High policy conflict suppresses exploration
        )

        # 4. Priority Modifier
        priority_mod = 1.0
        if signal.recent_success:
            priority_mod = 1.2
        elif signal.failure_pressure > 1.0:
            priority_mod = 0.8

        # [NEW] Counterfactual Influence on Priority
        # If we are missing opportunities but not blocked by policy, boost priority to break through
        if signal.missed_opportunity_pressure > 0.5 and signal.policy_conflict_density < 0.2:
            priority_mod += 0.1

        return StrategicMemoryContext(
            risk_bias=risk_bias,
            cooldown_required=cooldown,
            exploration_suppressed=exploration_suppressed,
            priority_modifier=priority_mod
        )