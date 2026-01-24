from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime
from typing import List

from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState
from src.core.domain.memory import MemorySystem
from src.core.domain.intention import Intention

@dataclass
class Stance:
    topics: dict = field(default_factory=dict)

@dataclass
class Goal:
    description: str
    priority: int

@dataclass
class AIHuman:
    id: UUID
    identity: Identity
    state: BehaviorState
    memory: MemorySystem
    stance: Stance
    goals: list[Goal]
    intentions: list[Intention] # [NEW]
    created_at: datetime

    @classmethod
    def create(cls, identity: Identity) -> 'AIHuman':
        return cls(
            id=uuid4(),
            identity=identity,
            state=BehaviorState(),
            memory=MemorySystem(),
            stance=Stance(),
            goals=[],
            intentions=[],
            created_at=datetime.utcnow()
        )

    def exist(self, current_time: datetime = None):
        """
        Passive existence loop (Stage 1 logic).
        """
        if current_time is None:
            current_time = datetime.utcnow()
        self.state.evolve_passive_state(current_time)
        self._cleanup_expired_intentions(current_time)

    def add_intention(self, intention: Intention):
        self.intentions.append(intention)
        # Sort by priority (descending)
        self.intentions.sort(key=lambda x: x.priority, reverse=True)

    def _cleanup_expired_intentions(self, current_time: datetime):
        # Silent expiration of intentions (The "Tragedy" of Stage 2)
        self.intentions = [i for i in self.intentions if not i.is_expired(current_time)]