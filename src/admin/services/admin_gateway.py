from typing import List, Optional, Tuple
from src.admin.interfaces.admin_gateway import AdminGateway
from src.admin.interfaces.governance_service import GovernanceService
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope

class StandardAdminGateway(AdminGateway):
    """
    Standard implementation of AdminGateway.
    Delegates strictly to GovernanceService.
    """
    def __init__(self, governance_service: GovernanceService):
        self.governance_service = governance_service

    def submit_command(self, command: AdminCommand) -> GovernanceDecision:
        return self.governance_service.process_command(command)

    def list_governance(self, scope: Optional[GovernanceScope] = None) -> List[GovernanceDecision]:
        return self.governance_service.get_active_decisions(scope)

    def get_audit_log(self) -> List[Tuple[AdminCommand, GovernanceDecision]]:
        return self.governance_service.get_audit_history()