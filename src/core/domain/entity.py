from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState
from src.core.domain.memory import MemorySystem


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
            created_at=datetime.utcnow()
        )

    def exist(self, current_time: datetime = None):
        """
        Passive existence loop.
        Updates internal state based on time passage.
        NO decisions are made here.
        NO actions are initiated here.
        """
        if current_time is None:
            current_time = datetime.utcnow()

        self.state.evolve_passive_state(current_time)