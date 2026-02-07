from abc import ABC, abstractmethod
from typing import List
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.admin.domain.governance_decision import GovernanceDecision

class GovernanceExecutionResolver(ABC):
    """
    Interface for applying governance decisions to the execution gate.
    Must be pure and deterministic.
    """
    @abstractmethod
    def apply(
        self,
        gate_decision: ExecutionGateDecision,
        governance: List[GovernanceDecision]
    ) -> ExecutionGateDecision:
        pass