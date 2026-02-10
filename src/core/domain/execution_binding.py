from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutionBindingSnapshot:
    """
    Read-only snapshot of state required for binding.
    Contains only primitives to ensure service purity.
    """
    energy_value: float
    fatigue_value: float
    readiness_value: float