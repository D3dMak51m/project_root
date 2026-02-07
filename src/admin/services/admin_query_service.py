from typing import List, Optional, Tuple
from src.admin.interfaces.admin_query_service import AdminQueryService
from src.admin.interfaces.admin_gateway import AdminGateway
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.admin_command import AdminCommand

class StandardAdminQueryService(AdminQueryService):
    """
    Implementation of AdminQueryService using AdminGateway.
    """
    def __init__(self, gateway: AdminGateway):
        self.gateway = gateway

    def get_active_decisions(self, scope: Optional[GovernanceScope] = None) -> List[GovernanceDecision]:
        return self.gateway.list_governance(scope)

    def get_audit_history(self) -> List[Tuple[AdminCommand, GovernanceDecision]]:
        return self.gateway.get_audit_log()