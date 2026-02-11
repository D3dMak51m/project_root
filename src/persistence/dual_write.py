from dataclasses import dataclass
from enum import Enum
from typing import List

from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.domain.event_record import EventRecord
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.memory.store.memory_store import MemoryStore
from src.world.context.context_buffer import ContextBuffer
from src.world.domain.world_observation import WorldObservation
from src.world.store.world_observation_store import WorldObservationStore


class CutoverPhase(Enum):
    PHASE_1_DUAL_WRITE = "phase_1_dual_write"
    PHASE_2_POSTGRES_READ_PRIMARY = "phase_2_postgres_read_primary"
    PHASE_3_POSTGRES_ONLY = "phase_3_postgres_only"


@dataclass
class DualWriteConfig:
    phase: CutoverPhase = CutoverPhase.PHASE_1_DUAL_WRITE

    @property
    def memory_write_enabled(self) -> bool:
        return self.phase in (
            CutoverPhase.PHASE_1_DUAL_WRITE,
            CutoverPhase.PHASE_2_POSTGRES_READ_PRIMARY,
        )

    @property
    def postgres_read_primary(self) -> bool:
        return self.phase in (
            CutoverPhase.PHASE_2_POSTGRES_READ_PRIMARY,
            CutoverPhase.PHASE_3_POSTGRES_ONLY,
        )


class DualWriteMemoryStore(MemoryStore):
    def __init__(
        self,
        memory_store: MemoryStore,
        postgres_store: MemoryStore,
        config: DualWriteConfig | None = None,
    ):
        super().__init__()
        self.memory_store = memory_store
        self.postgres_store = postgres_store
        self.config = config or DualWriteConfig()

    def append(self, event: EventRecord) -> None:
        self.postgres_store.append(event)
        if self.config.memory_write_enabled:
            self.memory_store.append(event)

    def list_all(self) -> List[EventRecord]:
        if self.config.postgres_read_primary:
            return self.postgres_store.list_all()
        return self.memory_store.list_all()


class DualWriteCounterfactualStore(CounterfactualMemoryStore):
    def __init__(
        self,
        memory_store: CounterfactualMemoryStore,
        postgres_store: CounterfactualMemoryStore,
        config: DualWriteConfig | None = None,
    ):
        super().__init__()
        self.memory_store = memory_store
        self.postgres_store = postgres_store
        self.config = config or DualWriteConfig()

    def append(self, event: CounterfactualEvent) -> None:
        self.postgres_store.append(event)
        if self.config.memory_write_enabled:
            self.memory_store.append(event)

    def list_all(self) -> List[CounterfactualEvent]:
        if self.config.postgres_read_primary:
            return self.postgres_store.list_all()
        return self.memory_store.list_all()

    def list_by_context(self, context_domain: str) -> List[CounterfactualEvent]:
        if self.config.postgres_read_primary and hasattr(self.postgres_store, "list_by_context"):
            return self.postgres_store.list_by_context(context_domain)
        if hasattr(self.memory_store, "list_by_context"):
            return self.memory_store.list_by_context(context_domain)
        return [e for e in self.list_all() if e.context_domain == context_domain]


class DualWriteWorldObservationStore(WorldObservationStore):
    def __init__(
        self,
        memory_store: WorldObservationStore,
        postgres_store: WorldObservationStore,
        config: DualWriteConfig | None = None,
    ):
        super().__init__()
        self.memory_store = memory_store
        self.postgres_store = postgres_store
        self.config = config or DualWriteConfig()

    def append(self, observation: WorldObservation) -> None:
        self.postgres_store.append(observation)
        if self.config.memory_write_enabled:
            self.memory_store.append(observation)

    def list_all(self) -> List[WorldObservation]:
        if self.config.postgres_read_primary:
            return self.postgres_store.list_all()
        return self.memory_store.list_all()

    def list_by_context(self, context_domain: str, limit: int = 100) -> List[WorldObservation]:
        if self.config.postgres_read_primary and hasattr(self.postgres_store, "list_by_context"):
            return self.postgres_store.list_by_context(context_domain, limit=limit)
        if hasattr(self.memory_store, "list_by_context"):
            return self.memory_store.list_by_context(context_domain, limit=limit)
        values = [x for x in self.list_all() if x.context_domain == context_domain]
        return values[-limit:]


class DualWriteContextBuffer(ContextBuffer):
    """
    Keeps memory and persistent buffers in sync during cutover.
    """

    def __init__(
        self,
        memory_buffer: ContextBuffer,
        postgres_buffer: ContextBuffer,
        config: DualWriteConfig | None = None,
    ):
        super().__init__()
        self.memory_buffer = memory_buffer
        self.postgres_buffer = postgres_buffer
        self.config = config or DualWriteConfig()

    def add(self, observation: WorldObservation) -> None:
        self.postgres_buffer.add(observation)
        if self.config.memory_write_enabled:
            self.memory_buffer.add(observation)

    def pop_all(self) -> List[WorldObservation]:
        if self.config.postgres_read_primary:
            primary = self.postgres_buffer.pop_all()
            if self.config.memory_write_enabled:
                self.memory_buffer.pop_all()
            return primary

        primary = self.memory_buffer.pop_all()
        self.postgres_buffer.pop_all()
        return primary

    def depth(self) -> int:
        if self.config.postgres_read_primary:
            return self.postgres_buffer.depth()
        return self.memory_buffer.depth()
