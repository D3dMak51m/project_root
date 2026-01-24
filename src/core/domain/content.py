from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

@dataclass
class ContentDraft:
    id: UUID
    action_id: UUID
    platform: str
    text: str
    style_notes: str
    created_at: datetime