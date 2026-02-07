from typing import List, Optional
from uuid import UUID
from src.admin.interfaces.governance_service import GovernanceService
from src.admin.interfaces.admin_command_handler import AdminCommandHandler
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.store.governance_state_store import GovernanceStateStore
from src.admin.store.audit_log_store import AuditLogStore
from src.admin.interfaces.governance_time_source import GovernanceTimeSource
from src.admin.interfaces.governance_id_source import GovernanceIdSource


class StandardGovernanceService(GovernanceService):
    """
    Standard implementation of GovernanceService.
    Orchestrates command handling, state updates, and audit logging.
    Uses injected sources for time and IDs to ensure determinism.
    """

    def __init__(
            self,
            handler: AdminCommandHandler,
            state_store: GovernanceStateStore,
            audit_store: AuditLogStore,
            time_source: GovernanceTimeSource,
            id_source: GovernanceIdSource
    ):
        self.handler = handler
        self.state_store = state_store
        self.audit_store = audit_store
        self.time_source = time_source
        self.id_source = id_source

    def process_command(self, command: AdminCommand) -> GovernanceDecision:
        # Inject deterministic values from sources
        decision_id = self.id_source.new_id()
        issued_at = self.time_source.now()

        # 1. Handle Command (Pure Logic)
        decision = self.handler.handle(command, decision_id, issued_at)

        # 2. Update State
        self.state_store.add(decision)

        # 3. Audit Log
        self.audit_store.append(command, decision)

        return decision

    def get_active_decisions(self, scope: Optional[GovernanceScope] = None) -> List[GovernanceDecision]:
        if scope:
            return self.state_store.list_by_scope(scope)
        return self.state_store.list_all()

    def get_decision(self, decision_id: UUID) -> Optional[GovernanceDecision]:
        return self.state_store.get(decision_id)