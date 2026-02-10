from dataclasses import dataclass
from enum import Enum
from typing import Optional
from src.interaction.domain.intent import InteractionIntent

class TargetHint(Enum):
    USER = "user"
    ADMIN = "admin"
    CHANNEL = "channel"
    BROADCAST = "broadcast"
    UNKNOWN = "unknown"

class PriorityHint(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

class Visibility(Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"

@dataclass(frozen=True)
class InteractionEnvelope:
    """
    Routed interaction intent with delivery hints.
    Does NOT guarantee delivery.
    """
    intent: InteractionIntent
    target_hint: TargetHint
    priority_hint: PriorityHint
    visibility: Visibility
    routing_key: Optional[str] = None # Abstract routing key (e.g., topic, user_id)