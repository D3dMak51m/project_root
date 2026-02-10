from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from enum import Enum

class DialogState(Enum):
    INITIATED = "INITIATED"
    CONSIDERING = "CONSIDERING"
    ACTIVE = "ACTIVE"
    STALLED = "STALLED"
    DISENGAGED = "DISENGAGED"
    TERMINATED = "TERMINATED"

@dataclass
class DialogSession:
    id: UUID
    target_person_id: UUID
    state: DialogState
    started_at: datetime
    last_activity: datetime