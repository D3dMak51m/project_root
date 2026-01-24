from dataclasses import dataclass
from typing import List
from uuid import UUID
from datetime import datetime

from .identity import Identity
from .behavior import BehaviorState
from .memory import MemorySystem
from .stance import Stance
from .readiness import ActionReadiness
from .intention import Intention
from .persona import PersonaMask

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
    created_at: datetime