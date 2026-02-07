from abc import ABC, abstractmethod
from src.admin.domain.governance_decision import GovernanceDecision

class EscalationReviewService(ABC):
    """
    Interface for reviewing and resolving escalations.
    """
    @abstractmethod
    def approve_escalation(self, escalation_id: str, reason: str) -> GovernanceDecision:
        pass

    @abstractmethod
    def reject_escalation(self, escalation_id: str, reason: str) -> GovernanceDecision:
        pass