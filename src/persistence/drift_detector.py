import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.domain.event_record import EventRecord
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.memory.store.memory_store import MemoryStore
from src.world.domain.world_observation import WorldObservation
from src.world.store.world_observation_store import WorldObservationStore


@dataclass(frozen=True)
class DriftReport:
    entity: str
    left_count: int
    right_count: int
    left_checksum: str
    right_checksum: str

    @property
    def clean(self) -> bool:
        return self.left_count == self.right_count and self.left_checksum == self.right_checksum


def _checksum(lines: Iterable[str]) -> str:
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _event_key(item: EventRecord) -> str:
    return f"{item.id}|{item.intent_id}|{item.context_domain}|{item.issued_at.isoformat()}|{item.execution_status.value}"


def _counterfactual_key(item: CounterfactualEvent) -> str:
    return f"{item.id}|{item.intent_id}|{item.context_domain}|{item.timestamp.isoformat()}|{item.suppression_stage}"


def _observation_key(item: WorldObservation) -> str:
    interaction_id = getattr(getattr(item, "interaction", None), "id", None)
    signal_source = getattr(getattr(item, "signal", None), "source_id", None)
    interaction_ts = getattr(getattr(item, "interaction", None), "timestamp", None)
    if isinstance(interaction_ts, datetime):
        observed_at = interaction_ts.isoformat()
    else:
        observed_at = "na"
    return f"{item.context_domain}|{interaction_id}|{signal_source}|{observed_at}"


def detect_memory_drift(
    left_store: MemoryStore,
    right_store: MemoryStore,
    context_domain: Optional[str] = None,
) -> DriftReport:
    left = left_store.list_all()
    right = right_store.list_all()
    if context_domain:
        left = [x for x in left if x.context_domain == context_domain]
        right = [x for x in right if x.context_domain == context_domain]
    left_keys = sorted(_event_key(x) for x in left)
    right_keys = sorted(_event_key(x) for x in right)
    return DriftReport(
        entity=f"memory:{context_domain or 'all'}",
        left_count=len(left_keys),
        right_count=len(right_keys),
        left_checksum=_checksum(left_keys),
        right_checksum=_checksum(right_keys),
    )


def detect_counterfactual_drift(
    left_store: CounterfactualMemoryStore,
    right_store: CounterfactualMemoryStore,
    context_domain: Optional[str] = None,
) -> DriftReport:
    left = left_store.list_all()
    right = right_store.list_all()
    if context_domain:
        left = [x for x in left if x.context_domain == context_domain]
        right = [x for x in right if x.context_domain == context_domain]
    left_keys = sorted(_counterfactual_key(x) for x in left)
    right_keys = sorted(_counterfactual_key(x) for x in right)
    return DriftReport(
        entity=f"counterfactual:{context_domain or 'all'}",
        left_count=len(left_keys),
        right_count=len(right_keys),
        left_checksum=_checksum(left_keys),
        right_checksum=_checksum(right_keys),
    )


def detect_world_observation_drift(
    left_store: WorldObservationStore,
    right_store: WorldObservationStore,
    context_domain: Optional[str] = None,
) -> DriftReport:
    left = left_store.list_all()
    right = right_store.list_all()
    if context_domain:
        left = [x for x in left if x.context_domain == context_domain]
        right = [x for x in right if x.context_domain == context_domain]
    left_keys = sorted(_observation_key(x) for x in left)
    right_keys = sorted(_observation_key(x) for x in right)
    return DriftReport(
        entity=f"world:{context_domain or 'all'}",
        left_count=len(left_keys),
        right_count=len(right_keys),
        left_checksum=_checksum(left_keys),
        right_checksum=_checksum(right_keys),
    )
