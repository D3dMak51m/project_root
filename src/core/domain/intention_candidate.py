from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class IntentionCandidate:
    """
    Transient impulse that may or may not become an Intention.
    Has no authority. Exists only within one LifeLoop tick.
    """
    topic: str
    pressure: float
    created_at: datetime