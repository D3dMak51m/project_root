from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID

class InteractionType(Enum):
    MESSAGE = "message"
    QUESTION = "question"
    REPORT = "report"
    NOTIFICATION = "notification"
    CONFIRMATION_REQUEST = "confirmation_request"

@dataclass(frozen=True)
class InteractionIntent:
    """
    Represents a potential communicative act.
    This is NOT an execution command. It describes WHAT to communicate, not HOW or WHEN.
    """
    id: UUID
    type: InteractionType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    target_id: Optional[str] = None # Abstract target identifier (e.g., user ID, channel ID)