from abc import ABC, abstractmethod
from typing import List
from src.interaction.domain.policy_decision import PolicyDecision
from src.admin.domain.governance_decision import GovernanceDecision

class GovernancePolicyResolver(ABC):
    """
    Interface for applying governance decisions to interaction policy.
    Must be pure and deterministic.
    """
    @abstractmethod
    def apply(
        self,
        decision: PolicyDecision,
        governance: List[GovernanceDecision]
    ) -> PolicyDecision:
        pass