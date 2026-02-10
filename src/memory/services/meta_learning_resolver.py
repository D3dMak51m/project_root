from src.memory.domain.strategic_learning_signal import StrategicLearningSignal
from src.memory.domain.meta_learning_context import MetaLearningContext


class MetaLearningResolver:
    """
    Pure service. Resolves whether and how to apply a learning signal
    based on the meta-learning context.
    """

    def resolve(
            self,
            signal: StrategicLearningSignal,
            context: MetaLearningContext
    ) -> StrategicLearningSignal:

        # 1. Hard Block: Learning Disabled or Governance Lock
        if not context.policy.learning_enabled or context.is_governance_locked:
            return self._null_signal()

        # 2. Stability Check
        if context.policy.require_stability_for_learning and not context.is_system_stable:
            return self._null_signal()

        # 3. Cooldown Check
        if context.ticks_since_last_failure < context.policy.cooldown_ticks_after_failure:
            return self._null_signal()

        # 4. Scaling / Dampening
        # Clamp priority bias to max delta
        max_delta = context.policy.max_learning_delta_per_tick
        clamped_bias = max(-max_delta, min(max_delta, signal.long_term_priority_bias))

        # If scaling is needed, we return a new signal with adjusted values.
        # Boolean flags are kept as is if allowed, or could be gated.
        # For M.7, we pass booleans but clamp the scalar bias.

        return StrategicLearningSignal(
            avoid_risk_patterns=signal.avoid_risk_patterns,
            reduce_exploration=signal.reduce_exploration,
            policy_pressure_high=signal.policy_pressure_high,
            governance_deadlock_detected=signal.governance_deadlock_detected,
            long_term_priority_bias=clamped_bias
        )

    def _null_signal(self) -> StrategicLearningSignal:
        return StrategicLearningSignal(
            avoid_risk_patterns=False,
            reduce_exploration=False,
            policy_pressure_high=False,
            governance_deadlock_detected=False,
            long_term_priority_bias=0.0
        )