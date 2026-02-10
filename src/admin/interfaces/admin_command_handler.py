from abc import ABC, abstractmethod
from uuid import UUID
from datetime import datetime
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_decision import GovernanceDecision

class AdminCommandHandler(ABC):
    """
    Interface for handling specific admin commands.
    Must be pure and deterministic.
    """
    @abstractmethod
    def handle(
        self,
        command: AdminCommand,
        decision_id: UUID,
        issued_at: datetime
    ) -> GovernanceDecision:
        pass