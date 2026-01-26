from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from datetime import datetime

@dataclass(frozen=True)
class PathStatus:
    failure_count: int
    last_outcome: str
    abandonment_level: str  # "none", "soft", "hard"
    last_updated: datetime
    # [NEW] Cooldown expiration time for soft abandonment
    cooldown_until: Optional[datetime] = None

@dataclass(frozen=True)
class StrategicMemory:
    """
    Context-scoped memory of strategic paths.
    Immutable snapshot.
    """
    # Key: abstract path tuple (e.g., ("communicate", "twitter"))
    # Value: PathStatus
    paths: Dict[Tuple[str, ...], PathStatus] = field(default_factory=dict)

    def get_status(self, path: Tuple[str, ...]) -> PathStatus:
        return self.paths.get(path, PathStatus(0, "none", "none", datetime.min, None))