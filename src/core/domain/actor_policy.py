from dataclasses import dataclass, field
from typing import List, Dict


@dataclass(frozen=True)
class ActorPolicy:
    """
    External constraints and rules for an Actor.
    Acts as a safety filter and capability definition.
    NOT part of the cognitive strategy.
    """
    # List of abstract actions this actor is allowed to perform
    allowed_actions: List[str]

    # Maximum risk level this actor will accept (0.0 - 1.0)
    max_risk_tolerance: float

    # Rate limits (e.g., {"post": 5, "like": 100} per hour)
    rate_limits: Dict[str, int] = field(default_factory=dict)

    # Environmental or ethical constraints
    # e.g., "no_political_content", "read_only_mode"
    constraints: List[str] = field(default_factory=list)