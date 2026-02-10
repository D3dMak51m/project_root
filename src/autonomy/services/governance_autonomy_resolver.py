from src.autonomy.interfaces.governance_autonomy_resolver import GovernanceAutonomyResolver
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext


class StandardGovernanceAutonomyResolver(GovernanceAutonomyResolver):
    """
    Deterministic resolver for autonomy governance.
    Applies pre-resolved governance state from context.
    """

    def apply(
            self,
            autonomy_state: AutonomyState,
            context: RuntimeGovernanceContext
    ) -> AutonomyState:

        # 1. Check Lock (Highest Priority)
        if context.is_autonomy_locked:
            return AutonomyState(
                mode=AutonomyMode.BLOCKED,
                justification=f"Governance Lock: {context.lock_reason}",
                pressure_level=0.0,
                constraints=autonomy_state.constraints + ["governance_lock"],
                requires_human=False
            )

        # 2. Check Override
        if context.override_mode:
            return AutonomyState(
                mode=context.override_mode,
                justification=f"Governance Override: {context.override_reason}",
                pressure_level=autonomy_state.pressure_level,
                constraints=autonomy_state.constraints,
                requires_human=autonomy_state.requires_human
            )

        # 3. Default (Pass-through)
        return autonomy_state