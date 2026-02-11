from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.core.domain.behavior import BehaviorState
from src.core.domain.entity import AIHuman
from src.core.domain.identity import Identity
from src.core.domain.memory import MemorySystem
from src.core.domain.readiness import ActionReadiness
from src.core.domain.stance import Stance
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.strategy import StrategicMode, StrategicPosture
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext
from src.hierarchy.domain.hierarchy_models import (
    HierarchyDirective,
    HierarchyGraph,
    HierarchyLevel,
    HierarchyNode,
)
from src.hierarchy.services.hierarchical_governance_resolver import HierarchicalGovernanceResolver
from src.hierarchy.services.hierarchy_projection_service import HierarchyProjectionService


@dataclass
class _StaticConfigLoader:
    graph: HierarchyGraph

    def load(self) -> HierarchyGraph:
        return self.graph


class _StaticRuntimeProvider:
    def get_context(self) -> RuntimeGovernanceContext:
        return RuntimeGovernanceContext(
            is_autonomy_locked=False,
            lock_reason="",
            override_mode=AutonomyMode.READY,
            override_reason="base",
            is_policy_rejected=False,
            policy_rejection_reason="",
            policy_constraints=["base_constraint"],
            is_execution_locked=False,
            execution_lock_reason="",
        )


def _human() -> AIHuman:
    now = datetime.now(timezone.utc)
    return AIHuman(
        id=uuid4(),
        identity=Identity("h", 0, "", "", [], [], {}),
        state=BehaviorState(100.0, 100.0, 0.0, now, False),
        memory=MemorySystem([], []),
        stance=Stance({}),
        readiness=ActionReadiness(0.0, 0.0, 100.0),
        intentions=[],
        personas=[],
        strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
        deferred_actions=[],
        created_at=now,
    )


def test_hierarchical_resolver_applies_top_down_precedence():
    directives = [
        HierarchyDirective(
            id=uuid4(),
            level=HierarchyLevel.L2,
            target="telegram:*",
            policy_constraints=["l2_constraint"],
        ),
        HierarchyDirective(
            id=uuid4(),
            level=HierarchyLevel.L1,
            target="platform:telegram",
            policy_constraints=["l1_constraint"],
            override_mode="SILENT",
        ),
        HierarchyDirective(
            id=uuid4(),
            level=HierarchyLevel.L0,
            target="*",
            execution_locked=True,
            reason="global_lock",
        ),
    ]
    graph = HierarchyGraph(
        nodes=[HierarchyNode(id="global", level=HierarchyLevel.L0, name="Global")],
        edges=[],
        directives=directives,
    )
    projection = HierarchyProjectionService(
        config_loader=_StaticConfigLoader(graph),
        override_store=None,
    )
    resolver = HierarchicalGovernanceResolver(
        projection_service=projection,
        runtime_provider=_StaticRuntimeProvider(),
    )
    context = StrategicContext(country="global", region=None, goal_id=None, domain="telegram:chat-1")

    resolved = resolver.resolve(context=context, human=_human())

    assert resolved.context.is_execution_locked is True
    assert resolved.context.execution_lock_reason == "global_lock"
    assert resolved.context.override_mode == AutonomyMode.SILENT
    assert "base_constraint" in resolved.context.policy_constraints
    assert "l1_constraint" in resolved.context.policy_constraints
    assert "l2_constraint" in resolved.context.policy_constraints
