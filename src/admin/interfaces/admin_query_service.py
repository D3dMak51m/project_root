from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.admin_command import AdminCommand

class AdminQueryService(ABC):
    """
    Interface for read-only admin queries.
    """
    @abstractmethod
    def get_active_decisions(self, scope: Optional[GovernanceScope] = None) -> List[GovernanceDecision]:
        pass

    @abstractmethod
    def get_audit_history(self) -> List[Tuple[AdminCommand, GovernanceDecision]]:
        pass