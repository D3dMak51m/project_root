from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime

@dataclass
class ContentDraft:
    id: UUID
    action_id: UUID
    platform: str

    text: str
    style_notes: str
    created_at: datetime

    @classmethod
    def create(cls, action_id: UUID, platform: str, text: str, style: str):
        return cls(
            id=uuid4(),
            action_id=action_id,
            platform=platform,
            text=text,
            style_notes=style,
            created_at=datetime.utcnow()
        )