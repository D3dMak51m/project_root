from dataclasses import dataclass


@dataclass(frozen=True)
class MemorySignal:
    """
    Aggregated signal derived from temporal memory analysis.
    Used by strategic layers to adjust behavior.
    """
    failure_pressure: float  # Weighted sum of recent failures
    recent_success: bool  # True if a success occurred in IMMEDIATE/RECENT window
    instability_detected: bool  # True if failure density is high
    governance_suppressed_ratio: float  # Ratio of events suppressed by governance in recent history

    # [NEW] Counterfactual Metrics
    missed_opportunity_pressure: float  # Pressure from suppressed high-value intents
    governance_friction_index: float  # 0.0-1.0, how much governance is blocking action
    policy_conflict_density: float  # Frequency of policy rejections