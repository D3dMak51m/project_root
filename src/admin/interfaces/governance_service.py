from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from uuid import UUID
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope

class GovernanceService(ABC):
    """
    Interface for the Governance Service.
    Manages admin commands, decisions, and state queries.
    """
    @abstractmethod
    def process_command(self, command: AdminCommand) -> GovernanceDecision:
        pass

    @abstractmethod
    def get_active_decisions(self, scope: Optional[GovernanceScope] = None) -> List[GovernanceDecision]:
        pass

    @abstractmethod
    def get_decision(self, decision_id: UUID) -> Optional[GovernanceDecision]:
        pass

    @abstractmethod
    def get_audit_history(self) -> List[Tuple[AdminCommand, GovernanceDecision]]:
        pass