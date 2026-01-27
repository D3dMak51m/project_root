from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum


class TrajectoryStatus(Enum):
    ACTIVE = "ACTIVE"
    STALLED = "STALLED"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True)
class StrategicTrajectory:
    """
    Represents a long-term strategic commitment or line of effort.
    Context-scoped.
    """
    id: str  # e.g., "expand_social_presence"
    status: TrajectoryStatus
    commitment_weight: float  # 0.0 - 1.0
    created_at: datetime
    last_updated: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategicTrajectory':
        return cls(
            id=data['id'],
            status=TrajectoryStatus(data['status']),
            commitment_weight=data['commitment_weight'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_updated=datetime.fromisoformat(data['last_updated'])
        )


@dataclass(frozen=True)
class StrategicTrajectoryMemory:
    """
    Immutable snapshot of all strategic trajectories for a context.
    """
    # Key: trajectory_id
    trajectories: Dict[str, StrategicTrajectory] = field(default_factory=dict)

    def get_trajectory(self, trajectory_id: str) -> Optional[StrategicTrajectory]:
        return self.trajectories.get(trajectory_id)