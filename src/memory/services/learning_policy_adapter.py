from src.memory.domain.strategic_learning_signal import StrategicLearningSignal
from src.core.domain.strategy import StrategicPosture


class LearningPolicyAdapter:
    """
    Pure service. Adapts StrategicPosture based on learned signals.
    This is a slow, long-term adjustment mechanism.
    """

    def adapt_posture(
            self,
            posture: StrategicPosture,
            signal: StrategicLearningSignal
    ) -> StrategicPosture:

        new_risk = posture.risk_tolerance
        new_confidence = posture.confidence_baseline
        new_persistence = posture.persistence_factor

        # 1. Risk Tolerance Adjustment
        if signal.avoid_risk_patterns:
            new_risk = max(0.1, new_risk - 0.05)
        elif signal.reduce_exploration:
            new_risk = max(0.1, new_risk - 0.02)

        # 2. Confidence Adjustment
        if signal.governance_deadlock_detected:
            new_confidence = max(0.1, new_confidence - 0.05)
        elif signal.policy_pressure_high:
            new_confidence = max(0.1, new_confidence - 0.02)

        # 3. Persistence Adjustment
        # If deadlock, reduce persistence (don't bang head against wall)
        if signal.governance_deadlock_detected:
            new_persistence = max(0.5, new_persistence - 0.1)

        # Apply bias to risk/confidence generally?
        # Or just use bias for priority?
        # The signal has 'long_term_priority_bias' which might be used elsewhere,
        # but here we adapt the posture itself.
        # Let's use bias to nudge risk tolerance slightly.
        new_risk = max(0.1, min(0.9, new_risk + (signal.long_term_priority_bias * 0.1)))

        return posture.update(
            risk_tolerance=new_risk,
            confidence_baseline=new_confidence,
            persistence_factor=new_persistence
        )