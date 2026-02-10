import pytest
from uuid import uuid4
from datetime import datetime
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.services.admin_query_service import StandardAdminQueryService
from src.admin.services.admin_gateway import StandardAdminGateway
from src.admin.services.governance_service import StandardGovernanceService
from src.admin.services.admin_command_handler import StaticAdminCommandHandler
from src.admin.store.governance_state_store import GovernanceStateStore
from src.admin.store.audit_log_store import AuditLogStore
from src.admin.tests.test_governance_service import FixedTimeSource, FixedIdSource


@pytest.fixture
def query_service():
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    fixed_id = uuid4()
    gov_service = StandardGovernanceService(
        StaticAdminCommandHandler(),
        GovernanceStateStore(),
        AuditLogStore(),
        FixedTimeSource(fixed_time),
        FixedIdSource(fixed_id)
    )
    gateway = StandardAdminGateway(gov_service)
    return StandardAdminQueryService(gateway)


def test_query_active_decisions(query_service):
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.LOCK_AUTONOMY,
        scope=GovernanceScope.AUTONOMY
    )
    query_service.gateway.submit_command(cmd)

    decisions = query_service.get_active_decisions(GovernanceScope.AUTONOMY)
    assert len(decisions) == 1
    assert decisions[0].action == GovernanceAction.LOCK_AUTONOMY


def test_query_audit_history(query_service):
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.REJECT,
        scope=GovernanceScope.POLICY
    )
    query_service.gateway.submit_command(cmd)

    history = query_service.get_audit_history()
    assert len(history) == 1
    assert history[0][0] == cmd