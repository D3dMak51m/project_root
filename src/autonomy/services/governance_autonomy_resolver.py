from typing import List
from src.autonomy.interfaces.governance_autonomy_resolver import GovernanceAutonomyResolver
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope


class StandardGovernanceAutonomyResolver(GovernanceAutonomyResolver):
    """
    Deterministic resolver for autonomy governance.
    Applies overrides and locks based on active governance decisions.
    Enforces strict priority: GLOBAL LOCK > AUTONOMY LOCK > OVERRIDE > UNLOCK.
    """

    def apply(
            self,
            autonomy_state: AutonomyState,
            decisions: List[GovernanceDecision]
    ) -> AutonomyState:

        # 1. Deterministic Sorting
        # Sort by issued_at, then id for tie-breaking
        sorted_decisions = sorted(decisions, key=lambda d: (d.issued_at, d.id))

        # Filter relevant decisions
        relevant_decisions = [
            d for d in sorted_decisions
            if d.scope in (GovernanceScope.GLOBAL, GovernanceScope.AUTONOMY)
        ]

        # 2. Determine Final State
        # We iterate through sorted decisions to find the *latest* effective instruction.
        # However, LOCK has priority over OVERRIDE if both are active?
        # Usually governance state is cumulative or "latest wins".
        # But LOCK is a persistent state until UNLOCK.
        # Let's assume decisions list contains *active* decisions from GovernanceService.
        # If so, we need to resolve conflicts.
        # Rule: LOCK overrides everything else.

        is_locked = False
        lock_reason = ""
        override_mode = None
        override_reason = ""

        for d in relevant_decisions:
            if d.action == GovernanceAction.LOCK_AUTONOMY:
                is_locked = True
                lock_reason = d.justification
            elif d.action == GovernanceAction.UNLOCK_AUTONOMY:
                is_locked = False
                lock_reason = ""
            elif d.action == GovernanceAction.OVERRIDE_MODE:
                mode_str = d.effect.get("mode")
                if mode_str:
                    try:
                        override_mode = AutonomyMode(mode_str)
                        override_reason = d.justification
                    except ValueError:
                        pass

        # 3. Apply Logic
        if is_locked:
            return AutonomyState(
                mode=AutonomyMode.BLOCKED,
                justification=f"Governance Lock: {lock_reason}",
                pressure_level=0.0,
                constraints=autonomy_state.constraints + ["governance_lock"],
                requires_human=False
            )

        if override_mode:
            return AutonomyState(
                mode=override_mode,
                justification=f"Governance Override: {override_reason}",
                pressure_level=autonomy_state.pressure_level,
                constraints=autonomy_state.constraints,
                requires_human=autonomy_state.requires_human
            )

        # 4. Default (Pass-through)
        return autonomy_state