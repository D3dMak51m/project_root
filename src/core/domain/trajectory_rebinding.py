from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class TrajectoryRebinding:
    """
    Represents a transfer of commitment from one trajectory to another.
    """
    source_trajectory_id: str
    target_trajectory_id: str
    transferred_weight: float
    reason: str
    created_at: datetime