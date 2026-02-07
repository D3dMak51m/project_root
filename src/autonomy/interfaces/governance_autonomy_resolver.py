from abc import ABC, abstractmethod
from typing import List
from src.autonomy.domain.autonomy_state import AutonomyState
from src.admin.domain.governance_decision import GovernanceDecision

class GovernanceAutonomyResolver(ABC):
    """
    Interface for applying governance decisions to autonomy state.
    Must be pure and deterministic.
    """
    @abstractmethod
    def apply(
        self,
        autonomy_state: AutonomyState,
        decisions: List[GovernanceDecision]
    ) -> AutonomyState:
        pass