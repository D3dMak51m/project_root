import pytest
from uuid import uuid4
from datetime import datetime
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.services.governance_service import StandardGovernanceService
from src.admin.services.admin_command_handler import StaticAdminCommandHandler
from src.admin.store.governance_state_store import GovernanceStateStore
from src.admin.store.audit_log_store import AuditLogStore
from src.admin.tests.test_governance_service import FixedTimeSource, FixedIdSource
from src.governance.runtime.governance_runtime_provider import GovernanceRuntimeProvider
from src.autonomy.services.governance_autonomy_resolver import StandardGovernanceAutonomyResolver
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode


@pytest.fixture
def governance_service():
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    fixed_id = uuid4()
    return StandardGovernanceService(
        StaticAdminCommandHandler(),
        GovernanceStateStore(),
        AuditLogStore(),
        FixedTimeSource(fixed_time),
        FixedIdSource(fixed_id)
    )


def test_context_conflict_resolution(governance_service):
    # Lock then Unlock
    cmd1 = AdminCommand(uuid4(), GovernanceAction.LOCK_AUTONOMY, GovernanceScope.AUTONOMY)
    cmd2 = AdminCommand(uuid4(), GovernanceAction.UNLOCK_AUTONOMY, GovernanceScope.AUTONOMY)

    governance_service.process_command(cmd1)
    governance_service.process_command(cmd2)

    provider = GovernanceRuntimeProvider(governance_service)
    context = provider.get_context()

    assert not context.is_autonomy_locked
    assert context.lock_reason == ""


def test_context_override_precedence(governance_service):
    # Override then Lock
    cmd1 = AdminCommand(uuid4(), GovernanceAction.OVERRIDE_MODE, GovernanceScope.AUTONOMY, payload={"mode": "SILENT"})
    cmd2 = AdminCommand(uuid4(), GovernanceAction.LOCK_AUTONOMY, GovernanceScope.AUTONOMY)

    governance_service.process_command(cmd1)
    governance_service.process_command(cmd2)

    provider = GovernanceRuntimeProvider(governance_service)
    context = provider.get_context()

    # Lock should be active
    assert context.is_autonomy_locked
    # Override is still present in state but resolver handles precedence
    assert context.override_mode == AutonomyMode.SILENT


def test_resolver_lock_wins(governance_service):
    provider = GovernanceRuntimeProvider(governance_service)
    resolver = StandardGovernanceAutonomyResolver()
    base_state = AutonomyState(AutonomyMode.READY, "test", 0.5, [], False)

    # Setup: Override to READY, but Lock active
    cmd1 = AdminCommand(uuid4(), GovernanceAction.OVERRIDE_MODE, GovernanceScope.AUTONOMY, payload={"mode": "READY"})
    cmd2 = AdminCommand(uuid4(), GovernanceAction.LOCK_AUTONOMY, GovernanceScope.AUTONOMY)

    governance_service.process_command(cmd1)
    governance_service.process_command(cmd2)

    context = provider.get_context()
    state = resolver.apply(base_state, context)

    assert state.mode == AutonomyMode.BLOCKED
    assert "Governance Lock" in state.justification


def test_execution_lock(governance_service):
    provider = GovernanceRuntimeProvider(governance_service)

    cmd = AdminCommand(uuid4(), GovernanceAction.IMPOSE_CONSTRAINT, GovernanceScope.EXECUTION,
                       payload={"constraint": "EMERGENCY_STOP"})
    governance_service.process_command(cmd)

    context = provider.get_context()
    assert context.is_execution_locked
    assert "EMERGENCY_STOP" in context.execution_lock_reason