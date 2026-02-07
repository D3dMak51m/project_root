import pytest
from uuid import UUID, uuid4
from datetime import datetime
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.services.governance_service import StandardGovernanceService
from src.admin.services.admin_command_handler import StaticAdminCommandHandler
from src.admin.store.governance_state_store import GovernanceStateStore
from src.admin.store.audit_log_store import AuditLogStore
from src.admin.interfaces.governance_time_source import GovernanceTimeSource
from src.admin.interfaces.governance_id_source import GovernanceIdSource


# --- Mocks ---

class FixedTimeSource(GovernanceTimeSource):
    def __init__(self, fixed_time: datetime):
        self.fixed_time = fixed_time

    def now(self) -> datetime:
        return self.fixed_time


class FixedIdSource(GovernanceIdSource):
    def __init__(self, fixed_id: UUID):
        self.fixed_id = fixed_id

    def new_id(self) -> UUID:
        return self.fixed_id


# --- Fixtures ---

@pytest.fixture
def fixed_time():
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def fixed_id():
    return uuid4()


@pytest.fixture
def service(fixed_time, fixed_id):
    return StandardGovernanceService(
        StaticAdminCommandHandler(),
        GovernanceStateStore(),
        AuditLogStore(),
        FixedTimeSource(fixed_time),
        FixedIdSource(fixed_id)
    )


# --- Tests ---

def test_process_command_determinism(service, fixed_time, fixed_id):
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.LOCK_AUTONOMY,
        scope=GovernanceScope.AUTONOMY
    )

    decision = service.process_command(cmd)

    # Strict equality check
    assert decision.id == fixed_id
    assert decision.issued_at == fixed_time
    assert decision.command_id == cmd.id
    assert decision.action == GovernanceAction.LOCK_AUTONOMY
    assert decision.scope == GovernanceScope.AUTONOMY


def test_state_persistence(service, fixed_id):
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.IMPOSE_CONSTRAINT,
        scope=GovernanceScope.POLICY,
        payload={"constraint": "no_politics"}
    )

    decision = service.process_command(cmd)
    stored = service.get_decision(fixed_id)

    assert stored == decision
    assert len(service.get_active_decisions(GovernanceScope.POLICY)) == 1


def test_audit_logging(service):
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.APPROVE,
        scope=GovernanceScope.ESCALATION,
        target_id="esc_123"
    )

    decision = service.process_command(cmd)
    history = service.audit_store.get_history()

    assert len(history) == 1
    assert history[0][0] == cmd
    assert history[0][1] == decision