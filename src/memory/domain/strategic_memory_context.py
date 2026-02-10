from dataclasses import dataclass

@dataclass(frozen=True)
class StrategicMemoryContext:
    """
    Immutable context derived from memory signals.
    Modulates strategic behavior without overriding governance.
    """
    risk_bias: float             # -1.0 (averse) to 1.0 (seeking)
    cooldown_required: bool      # If true, system should pause active initiatives
    exploration_suppressed: bool # If true, stick to known paths
    priority_modifier: float     # Multiplier for intent priority (0.5 - 1.5)