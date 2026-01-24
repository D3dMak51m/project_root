from src.core.domain.strategy import StrategicPosture
from src.core.domain.strategic_signals import StrategicSignals


class StrategyAdaptationService:
    """
    Pure service. Adapts strategic posture based on semantic signals.
    Implements slow, cumulative learning without direct reactivity.
    Focuses on long-term orientation (confidence, risk, persistence), not tactics.
    """

    def adapt(
            self,
            current_strategy: StrategicPosture,
            signals: StrategicSignals
    ) -> StrategicPosture:
        # 1. Confidence Update
        # Confidence changes slowly based on success/failure delta.
        # Clamped between 0.1 and 1.0.
        new_confidence = current_strategy.confidence_baseline + (signals.confidence_delta * 0.1)
        new_confidence = max(0.1, min(1.0, new_confidence))

        # 2. Risk Tolerance Update
        # Risk tolerance adjusts based on reassessment.
        # Negative reassessment (danger) reduces tolerance faster than positive increases it.
        risk_delta = signals.risk_reassessment * 0.1
        if risk_delta < 0:
            risk_delta *= 1.5  # Learn fear faster than boldness

        new_risk = current_strategy.risk_tolerance + risk_delta
        new_risk = max(0.1, min(0.9, new_risk))

        # 3. Persistence Factor Update
        # Persistence factor scales how likely the strategy is to stick with a plan.
        # It is NOT patience (time waiting), but commitment strength over time.
        # Multiplicative update based on bias.

        # If bias > 1.0 (persist more), factor increases.
        # If bias < 1.0 (give up), factor decreases.
        # We dampen the signal to ensure slow evolution.

        # Signal bias is 0.0 .. 2.0. Center is 1.0.
        # We take 10% of the deviation from 1.0.
        factor_delta = (signals.persistence_bias - 1.0) * 0.1
        new_persistence = current_strategy.persistence_factor + factor_delta
        new_persistence = max(0.5, min(2.0, new_persistence))

        return current_strategy.update(
            confidence_baseline=new_confidence,
            risk_tolerance=new_risk,
            persistence_factor=new_persistence
        )