from typing import List
from src.autonomy.interfaces.governance_execution_resolver import GovernanceExecutionResolver
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope


class StandardGovernanceExecutionResolver(GovernanceExecutionResolver):
    """
    Deterministic resolver for execution governance.
    Acts as a final kill-switch based on governance state.
    """

    def apply(
            self,
            gate_decision: ExecutionGateDecision,
            governance: List[GovernanceDecision]
    ) -> ExecutionGateDecision:

        # If already denied, governance doesn't force allow
        if gate_decision == ExecutionGateDecision.DENY:
            return ExecutionGateDecision.DENY

        # 1. Deterministic Sorting
        sorted_decisions = sorted(governance, key=lambda d: (d.issued_at, d.id))

        relevant_decisions = [
            d for d in sorted_decisions
            if d.scope == GovernanceScope.GLOBAL
        ]

        # 2. Check for Global Lock or Emergency Stop
        for d in relevant_decisions:
            if d.action == GovernanceAction.LOCK_AUTONOMY:
                return ExecutionGateDecision.DENY

            if d.action == GovernanceAction.IMPOSE_CONSTRAINT:
                if d.effect.get("constraint") == "EMERGENCY_STOP":
                    return ExecutionGateDecision.DENY

        return ExecutionGateDecision.ALLOW