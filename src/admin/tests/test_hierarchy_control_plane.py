from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.admin.services.control_plane_service import AdminControlPlaneService
from src.core.ledger.in_memory_ledger import InMemoryStrategicLedger
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.persistence.in_memory_backend import InMemoryStrategicStateBackend
from src.core.time.frozen_time_source import FrozenTimeSource
from src.execution.queue.execution_queue import InMemoryExecutionQueue
from src.hierarchy.domain.hierarchy_models import (
    HierarchyDirective,
    HierarchyEdge,
    HierarchyGraph,
    HierarchyLevel,
    HierarchyNode,
)
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.memory.store.memory_store import MemoryStore
from src.world.store.world_observation_store import WorldObservationStore


class _Projection:
    def build_graph(self):
        return HierarchyGraph(
            nodes=[HierarchyNode(id="global", level=HierarchyLevel.L0, name="Global")],
            edges=[HierarchyEdge(parent_id="global", child_id="telegram")],
            directives=[],
        )


class _OverrideStore:
    def __init__(self):
        self.rows = {}

    def create_override(self, level, target, payload, actor):
        row_id = uuid4()
        self.rows[row_id] = HierarchyDirective(
            id=row_id,
            level=HierarchyLevel(level),
            target=target,
            metadata={"payload": payload, "actor": actor},
        )
        return row_id

    def deactivate_override(self, override_id):
        return override_id in self.rows

    def get(self, override_id):
        return self.rows.get(override_id)


@dataclass(frozen=True)
class _Agg:
    bucket_at: datetime
    level: HierarchyLevel
    key: str
    metrics: dict


class _AggStore:
    def list_aggregates(self, level=None, limit=200):
        rows = [
            _Agg(
                bucket_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
                level=HierarchyLevel.L1,
                key="telegram",
                metrics={"execution_total": 3.0},
            )
        ]
        if level:
            return [row for row in rows if row.level == level][:limit]
        return rows[:limit]


def _service():
    now = datetime(2025, 2, 5, tzinfo=timezone.utc)
    orchestrator = StrategicOrchestrator(
        time_source=FrozenTimeSource(now),
        ledger=InMemoryStrategicLedger(),
        backend=InMemoryStrategicStateBackend(),
        execution_queue=InMemoryExecutionQueue(),
    )
    return AdminControlPlaneService(
        orchestrator=orchestrator,
        execution_queue=InMemoryExecutionQueue(),
        world_store=WorldObservationStore(),
        memory_store=MemoryStore(),
        counterfactual_store=CounterfactualMemoryStore(),
        hierarchy_projection_service=_Projection(),
        hierarchy_override_store=_OverrideStore(),
        upward_aggregation_service=_AggStore(),
    )


def test_control_plane_exposes_hierarchy_tree_and_aggregates():
    service = _service()

    tree = service.get_hierarchy_tree()
    agg = service.get_hierarchy_aggregates(level="L1")

    assert len(tree["nodes"]) == 1
    assert tree["nodes"][0]["id"] == "global"
    assert len(agg) == 1
    assert agg[0]["level"] == "L1"


def test_hierarchy_override_mutations_are_audited():
    service = _service()

    created = service.create_hierarchy_override(
        level="L2",
        target="telegram:*",
        payload={"execution_locked": True},
        actor="admin-1",
        role="admin",
    )
    assert created is not None
    override_id = UUID(created["id"])

    deleted = service.delete_hierarchy_override(override_id=override_id, actor="admin-1", role="admin")
    assert deleted is True

    audits = service.get_mutation_audit(limit=10)
    assert len(audits) == 2
    assert audits[0].action == "hierarchy_override_create"
    assert audits[1].action == "hierarchy_override_delete"

