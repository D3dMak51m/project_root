from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime


class ExecutionStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"


class ExecutionFailureType(Enum):
    """
    Categorizes the source of the failure or rejection.
    """
    POLICY = "POLICY"  # Blocked by ActorPolicy (e.g., risk too high)
    ENVIRONMENT = "ENVIRONMENT"  # External system failure (e.g., API timeout)
    INTERNAL = "INTERNAL"  # Actor internal error (e.g., serialization fail)
    NONE = "NONE"  # No failure (Success)


@dataclass(frozen=True)
class ExecutionResult:
    """
    Represents the outcome of an attempted action by an Actor.
    Describes WHAT HAPPENED, not what was planned.
    This is NOT memory, but raw feedback from the world.
    """
    status: ExecutionStatus
    timestamp: datetime

    # Actual effects produced in the world (e.g., "message_sent", "file_created")
    effects: List[str] = field(default_factory=list)

    # Actual costs incurred (e.g., API tokens, time, energy)
    costs: Dict[str, float] = field(default_factory=dict)

    # Observations made during execution (e.g., "error_message", "reply_count")
    observations: Dict[str, Any] = field(default_factory=dict)

    # Structured failure categorization
    failure_type: ExecutionFailureType = ExecutionFailureType.NONE

    # Human-readable explanation (optional)
    reason: str = ""