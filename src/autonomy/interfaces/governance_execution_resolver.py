from abc import ABC, abstractmethod
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext

class GovernanceExecutionResolver(ABC):
    """
    Interface for applying governance decisions to the execution gate.
    Must be pure and deterministic.
    """
    @abstractmethod
    def apply(
        self,
        gate_decision: ExecutionGateDecision,
        context: RuntimeGovernanceContext
    ) -> ExecutionGateDecision:
        pass