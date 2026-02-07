from abc import ABC, abstractmethod
from src.interaction.domain.policy_decision import PolicyDecision
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext

class GovernancePolicyResolver(ABC):
    """
    Interface for applying governance decisions to interaction policy.
    Must be pure and deterministic.
    """
    @abstractmethod
    def apply(
        self,
        decision: PolicyDecision,
        context: RuntimeGovernanceContext
    ) -> PolicyDecision:
        pass