from dataclasses import dataclass
from typing import List, Dict
from src.core.domain.strategy import StrategicMode
from src.core.domain.strategic_trajectory import StrategicTrajectory
from src.core.domain.strategic_memory import PathStatus


@dataclass(frozen=True)
class StrategicSnapshot:
    """
    Read-only view of the agent's strategic state.
    """
    mode: StrategicMode
    horizon_days: int
    confidence: float
    risk_tolerance: float
    persistence_factor: float

    active_trajectories: List[StrategicTrajectory]
    stalled_trajectories: List[StrategicTrajectory]
    abandoned_trajectories: List[StrategicTrajectory]

    path_statuses: Dict[str, PathStatus]  # Key as string representation of tuple