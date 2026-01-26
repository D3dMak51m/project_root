from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class ReflectionOutcome(Enum):
    RETRY = "RETRY"
    TRANSFORM = "TRANSFORM"
    ABANDON = "ABANDON"

class InferredCause(Enum):
    POLICY = "POLICY"
    ENVIRONMENT = "ENVIRONMENT"
    MISALIGNMENT = "MISALIGNMENT"
    RESOURCE = "RESOURCE"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class StrategicReflection:
    """
    Immutable analysis of a strategic trajectory's state.
    Determines the next strategic move (retry, transform, abandon).
    """
    trajectory_id: str
    outcome: ReflectionOutcome
    inferred_cause: InferredCause
    confidence_adjustment: float
    generated_at: datetime