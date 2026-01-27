from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any
from datetime import datetime

@dataclass(frozen=True)
class PathStatus:
    failure_count: int
    last_outcome: str
    abandonment_level: str  # "none", "soft", "hard"
    last_updated: datetime
    cooldown_until: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PathStatus':
        return cls(
            failure_count=data['failure_count'],
            last_outcome=data['last_outcome'],
            abandonment_level=data['abandonment_level'],
            last_updated=datetime.fromisoformat(data['last_updated']),
            cooldown_until=datetime.fromisoformat(data['cooldown_until']) if data.get('cooldown_until') else None
        )

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