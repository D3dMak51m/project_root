from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class HierarchyLevel(Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


@dataclass(frozen=True)
class HierarchyDirective:
    id: UUID
    level: HierarchyLevel
    target: str
    reason: str = ""
    execution_locked: Optional[bool] = None
    autonomy_locked: Optional[bool] = None
    override_mode: Optional[str] = None
    policy_constraints: List[str] = field(default_factory=list)
    budget_cap: Optional[float] = None
    priority_bias: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class HierarchyNode:
    id: str
    level: HierarchyLevel
    name: str
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HierarchyEdge:
    parent_id: str
    child_id: str


@dataclass(frozen=True)
class HierarchyGraph:
    nodes: List[HierarchyNode] = field(default_factory=list)
    edges: List[HierarchyEdge] = field(default_factory=list)
    directives: List[HierarchyDirective] = field(default_factory=list)

    @staticmethod
    def default() -> "HierarchyGraph":
        return HierarchyGraph(
            nodes=[HierarchyNode(id="global", level=HierarchyLevel.L0, name="Global")],
            edges=[],
            directives=[],
        )


def directive_from_payload(payload: Dict[str, Any]) -> HierarchyDirective:
    raw_level = str(payload.get("level", "L0")).upper()
    try:
        level = HierarchyLevel(raw_level)
    except Exception:
        level = HierarchyLevel.L0

    constraints = payload.get("policy_constraints", [])
    if not isinstance(constraints, list):
        constraints = []

    return HierarchyDirective(
        id=UUID(str(payload["id"])) if payload.get("id") else uuid4(),
        level=level,
        target=str(payload.get("target", "*")),
        reason=str(payload.get("reason", "")),
        execution_locked=payload.get("execution_locked"),
        autonomy_locked=payload.get("autonomy_locked"),
        override_mode=payload.get("override_mode"),
        policy_constraints=[str(x) for x in constraints],
        budget_cap=float(payload["budget_cap"]) if payload.get("budget_cap") is not None else None,
        priority_bias=float(payload["priority_bias"]) if payload.get("priority_bias") is not None else None,
        metadata=dict(payload.get("metadata") or {}),
        created_at=payload.get("created_at") or datetime.now(timezone.utc),
    )

