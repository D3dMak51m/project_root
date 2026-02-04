from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

@dataclass(frozen=True)
class RawSignal:
    """
    Raw data received from an external source.
    Contains no interpretation, only the payload and metadata.
    """
    source_id: str          # e.g., "rss:bbc", "api:twitter"
    received_at: datetime
    payload: Any            # raw text, json dict, html string, etc.

@dataclass(frozen=True)
class NormalizedSignal:
    """
    Canonical representation of an ingested signal.
    Ready for storage and downstream processing.
    """
    signal_id: UUID
    source_id: str
    received_at: datetime
    observed_at: datetime   # When the event actually happened (if known)
    content: str            # Cleaned text or serialized content
    metadata: Dict[str, Any] = field(default_factory=dict)