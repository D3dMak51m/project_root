from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from src.core.domain.strategic_context import StrategicContext

@dataclass(frozen=True)
class StrategicEvent:
    """
    Immutable record of a strategic change.
    Context is a first-class attribute, ensuring strict isolation.
    """
    id: UUID
    timestamp: datetime
    event_type: str  # e.g., "MODE_SHIFT", "TRAJECTORY_UPDATE", "PATH_ABANDONMENT"
    details: Dict[str, Any]
    context: StrategicContext # [UPDATED] Replaces context_domain string