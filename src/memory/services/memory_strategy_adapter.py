from src.memory.domain.memory_signal import MemorySignal
from src.memory.domain.strategic_memory_context import StrategicMemoryContext


class MemoryStrategyAdapter:
    """
    Pure service. Translates raw MemorySignal into actionable StrategicMemoryContext.
    """

    def adapt(self, signal: MemorySignal) -> StrategicMemoryContext:
        # 1. Risk Bias Calculation
        # High failure pressure -> Risk Aversion
        # Recent success -> Slight Risk Seeking
        risk_bias = 0.0
        if signal.failure_pressure > 2.0:
            risk_bias = -0.5
        elif signal.failure_pressure > 0.5:
            risk_bias = -0.2

        if signal.recent_success:
            risk_bias += 0.1

        # Clamp risk bias
        risk_bias = max(-1.0, min(1.0, risk_bias))

        # 2. Cooldown Requirement
        # Instability -> Cooldown
        cooldown = signal.instability_detected

        # 3. Exploration Suppression
        # High governance suppression or instability -> Suppress exploration
        exploration_suppressed = (
                signal.instability_detected or
                signal.governance_suppressed_ratio > 0.3
        )

        # 4. Priority Modifier
        # Success boosts priority, failure dampens it
        priority_mod = 1.0
        if signal.recent_success:
            priority_mod = 1.2
        elif signal.failure_pressure > 1.0:
            priority_mod = 0.8

        return StrategicMemoryContext(
            risk_bias=risk_bias,
            cooldown_required=cooldown,
            exploration_suppressed=exploration_suppressed,
            priority_modifier=priority_mod
        )