from dataclasses import dataclass
from typing import Optional

from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.core.domain.entity import AIHuman
from src.core.domain.strategic_context import StrategicContext
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext
from src.governance.runtime.governance_runtime_provider import GovernanceRuntimeProvider
from src.hierarchy.services.hierarchy_projection_service import HierarchyProjectionService


def _empty_context() -> RuntimeGovernanceContext:
    return RuntimeGovernanceContext(
        is_autonomy_locked=False,
        lock_reason="",
        override_mode=None,
        override_reason="",
        is_policy_rejected=False,
        policy_rejection_reason="",
        policy_constraints=[],
        is_execution_locked=False,
        execution_lock_reason="",
    )


@dataclass(frozen=True)
class ResolvedGovernanceSource:
    context: RuntimeGovernanceContext
    source: str


class HierarchicalGovernanceResolver:
    """
    Applies hierarchy directives on top of runtime governance.
    Precedence is strict top-down: L0 > L1 > L2 > L3 > Persona.
    """

    def __init__(
        self,
        projection_service: HierarchyProjectionService,
        runtime_provider: Optional[GovernanceRuntimeProvider] = None,
    ):
        self.projection_service = projection_service
        self.runtime_provider = runtime_provider

    def resolve(self, context: StrategicContext, human: Optional[AIHuman] = None) -> ResolvedGovernanceSource:
        base = self.runtime_provider.get_context() if self.runtime_provider else _empty_context()
        effective = self.projection_service.resolve_for_context(context, human)

        is_execution_locked = bool(base.is_execution_locked)
        execution_reason = str(base.execution_lock_reason)
        is_autonomy_locked = bool(base.is_autonomy_locked)
        autonomy_reason = str(base.lock_reason)
        override_mode = base.override_mode
        override_reason = str(base.override_reason)
        policy_constraints = list(base.policy_constraints or [])

        for directive in effective.directives:
            if directive.execution_locked is True:
                is_execution_locked = True
                execution_reason = directive.reason or f"Hierarchy {directive.level.value} execution lock"
            if directive.autonomy_locked is True:
                is_autonomy_locked = True
                autonomy_reason = directive.reason or f"Hierarchy {directive.level.value} autonomy lock"
            if directive.override_mode:
                try:
                    override_mode = AutonomyMode(str(directive.override_mode))
                    override_reason = directive.reason or f"Hierarchy {directive.level.value} override"
                except Exception:
                    pass
            for constraint in directive.policy_constraints:
                if constraint not in policy_constraints:
                    policy_constraints.append(constraint)

        ctx = RuntimeGovernanceContext(
            is_autonomy_locked=is_autonomy_locked,
            lock_reason=autonomy_reason,
            override_mode=override_mode,
            override_reason=override_reason,
            is_policy_rejected=base.is_policy_rejected,
            policy_rejection_reason=base.policy_rejection_reason,
            policy_constraints=policy_constraints,
            is_execution_locked=is_execution_locked,
            execution_lock_reason=execution_reason,
        )
        return ResolvedGovernanceSource(context=ctx, source="hierarchical_overlay")

