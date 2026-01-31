from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

@dataclass(frozen=True)
class TelemetryEvent:
    """
    Immutable telemetry data point.
    Decoupled from internal domain events to allow schema evolution.
    """
    timestamp: datetime
    event_type: str
    source_component: str
    context_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    is_replay: bool = False