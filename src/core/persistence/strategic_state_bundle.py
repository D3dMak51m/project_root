from dataclasses import dataclass
from typing import Optional
from src.core.domain.strategy import StrategicPosture
from src.core.domain.strategic_memory import StrategicMemory
from src.core.domain.strategic_trajectory import StrategicTrajectoryMemory
from src.core.domain.strategic_snapshot import StrategicSnapshot

@dataclass(frozen=True)
class StrategicStateBundle:
    """
    Pure data object representing the full strategic state of an agent
    for a specific context at a specific point in time.
    Used for persistence and cold-start restoration.
    """
    posture: StrategicPosture
    memory: StrategicMemory
    trajectory_memory: StrategicTrajectoryMemory
    last_snapshot: Optional[StrategicSnapshot] = None
    version: str = "1.0"