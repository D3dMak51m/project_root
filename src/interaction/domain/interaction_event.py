from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class InteractionEvent:
    """
    Canonical representation of an external interaction event.
    Platform-agnostic.
    """
    id: UUID
    platform: str
    user_id: str
    chat_id: str
    content: str
    message_type: str # "text", "command", "image", etc.
    timestamp: datetime
    raw_metadata: dict