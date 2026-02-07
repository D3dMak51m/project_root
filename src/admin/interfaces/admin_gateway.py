from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope

class AdminGateway(ABC):
    """
    Application-level façade for administrative operations.
    Orchestrates commands and queries without adding business logic.
    """
    @abstractmethod
    def submit_command(self, command: AdminCommand) -> GovernanceDecision:
        pass

    @abstractmethod
    def list_governance(self, scope: Optional[GovernanceScope] = None) -> List[GovernanceDecision]:
        pass

    @abstractmethod
    def get_audit_log(self) -> List[Tuple[AdminCommand, GovernanceDecision]]:
        pass