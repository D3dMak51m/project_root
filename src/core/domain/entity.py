from dataclasses import dataclass
from typing import List
from uuid import UUID
from datetime import datetime

from .identity import Identity
from .behavior import BehaviorState
from .memory import MemorySystem
from .stance import Stance
from .readiness import ActionReadiness
from .intention import Intention, DeferredAction
from .persona import PersonaMask
from .strategy import StrategicPosture
# strategic_memory and strategic_trajectory_memory removed as they are context-scoped and stored externally

@dataclass
class AIHuman:
    id: UUID
    identity: Identity
    state: BehaviorState
    memory: MemorySystem
    stance: Stance
    readiness: ActionReadiness
    intentions: List[Intention]
    personas: List[PersonaMask]
    strategy: StrategicPosture
    deferred_actions: List[DeferredAction]
    created_at: datetime