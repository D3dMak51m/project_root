from dataclasses import dataclass

@dataclass(frozen=True)
class StrategicLearningSignal:
    """
    Immutable signal representing a learned strategic lesson.
    Derived from aggregated memory analysis.
    """
    avoid_risk_patterns: bool
    reduce_exploration: bool
    policy_pressure_high: bool
    governance_deadlock_detected: bool
    long_term_priority_bias: float  # -0.3 to +0.3