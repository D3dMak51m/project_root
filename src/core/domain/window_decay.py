from dataclasses import dataclass
from enum import Enum

class WindowDecayOutcome(Enum):
    PERSIST = "persist"
    CLOSE = "close"
    INVALIDATE = "invalidate"

@dataclass(frozen=True)
class ExecutionWindowDecayResult:
    """
    Read-only verdict describing what happened to the ExecutionWindow.
    """
    outcome: WindowDecayOutcome
    reason: str