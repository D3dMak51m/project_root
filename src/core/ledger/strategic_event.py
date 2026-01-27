from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

@dataclass(frozen=True)
class StrategicEvent:
    """
    Immutable record of a strategic change.
    """
    id: UUID
    timestamp: datetime
    event_type: str  # e.g., "MODE_SHIFT", "TRAJECTORY_UPDATE", "PATH_ABANDONMENT"
    details: Dict[str, Any]
    context_domain: str