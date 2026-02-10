from src.admin.interfaces.escalation_review_service import EscalationReviewService
from src.admin.interfaces.admin_gateway import AdminGateway
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.governance_decision import GovernanceDecision

class StandardEscalationReviewService(EscalationReviewService):
    """
    Deterministic implementation of EscalationReviewService.
    Translates review actions into AdminCommands via Gateway.
    Strictly pure translation: no ID generation, no time generation.
    """
    def __init__(self, gateway: AdminGateway):
        self.gateway = gateway

    def approve_escalation(self, escalation_id: str, reason: str) -> GovernanceDecision:
        command = AdminCommand(
            id=None, # ID generation delegated to client or handled by system if needed (but here we don't generate)
            action=GovernanceAction.APPROVE,
            scope=GovernanceScope.ESCALATION,
            target_id=escalation_id,
            payload={"reason": reason}
        )
        return self.gateway.submit_command(command)

    def reject_escalation(self, escalation_id: str, reason: str) -> GovernanceDecision:
        command = AdminCommand(
            id=None,
            action=GovernanceAction.REJECT,
            scope=GovernanceScope.ESCALATION,
            target_id=escalation_id,
            payload={"reason": reason}
        )
        return self.gateway.submit_command(command)