from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime

from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState
from src.core.domain.memory import MemorySystem


@dataclass
class Stance:
    """Placeholder for opinions and red lines"""
    topics: dict = field(default_factory=dict)


@dataclass
class Goal:
    """Placeholder for goals"""
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

    def live(self, current_time: datetime = None):
        """
        The heartbeat of the entity. Updates internal state based on time passed.
        Does NOT trigger external actions.
        """
        if current_time is None:
            current_time = datetime.utcnow()

        self.state.update_over_time(current_time)

    def rest(self):
        self.state.start_rest()

    def wake_up(self):
        self.state.stop_rest()