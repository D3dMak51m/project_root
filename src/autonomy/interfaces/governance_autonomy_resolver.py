from abc import ABC, abstractmethod
from src.autonomy.domain.autonomy_state import AutonomyState
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext

class GovernanceAutonomyResolver(ABC):
    """
    Interface for applying governance decisions to autonomy state.
    Must be pure and deterministic.
    """
    @abstractmethod
    def apply(
        self,
        autonomy_state: AutonomyState,
        context: RuntimeGovernanceContext
    ) -> AutonomyState:
        pass