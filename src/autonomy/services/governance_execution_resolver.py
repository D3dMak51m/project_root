from src.autonomy.interfaces.governance_execution_resolver import GovernanceExecutionResolver
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext


class StandardGovernanceExecutionResolver(GovernanceExecutionResolver):
    """
    Deterministic resolver for execution governance.
    Applies pre-resolved governance state from context.
    """

    def apply(
            self,
            gate_decision: ExecutionGateDecision,
            context: RuntimeGovernanceContext
    ) -> ExecutionGateDecision:

        # If already denied, governance doesn't force allow
        if gate_decision == ExecutionGateDecision.DENY:
            return ExecutionGateDecision.DENY

        # Check for Global Lock or Emergency Stop
        if context.is_execution_locked:
            return ExecutionGateDecision.DENY

        return ExecutionGateDecision.ALLOW