import pytest
from uuid import uuid4
from datetime import datetime
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.services.admin_gateway import StandardAdminGateway
from src.admin.services.governance_service import StandardGovernanceService
from src.admin.services.admin_command_handler import StaticAdminCommandHandler
from src.admin.store.governance_state_store import GovernanceStateStore
from src.admin.store.audit_log_store import AuditLogStore
from src.admin.tests.test_governance_service import FixedTimeSource, FixedIdSource

@pytest.fixture
def gateway():
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    fixed_id = uuid4()
    gov_service = StandardGovernanceService(
        StaticAdminCommandHandler(),
        GovernanceStateStore(),
        AuditLogStore(),
        FixedTimeSource(fixed_time),
        FixedIdSource(fixed_id)
    )
    return StandardAdminGateway(gov_service)

def test_gateway_submit_command(gateway):
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.LOCK_AUTONOMY,
        scope=GovernanceScope.AUTONOMY
    )
    decision = gateway.submit_command(cmd)
    assert decision.action == GovernanceAction.LOCK_AUTONOMY
    assert len(gateway.list_governance()) == 1

def test_gateway_audit_log(gateway):
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.IMPOSE_CONSTRAINT,
        scope=GovernanceScope.POLICY
    )
    gateway.submit_command(cmd)
    log = gateway.get_audit_log()
    assert len(log) == 1
    assert log[0][0] == cmd