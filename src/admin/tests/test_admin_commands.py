import pytest
from uuid import uuid4
from datetime import datetime
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.services.admin_command_handler import StaticAdminCommandHandler


def test_handler_determinism():
    handler = StaticAdminCommandHandler()
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.OVERRIDE_MODE,
        scope=GovernanceScope.AUTONOMY,
        payload={"mode": "SILENT"}
    )

    fixed_id = uuid4()
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)

    d1 = handler.handle(cmd, fixed_id, fixed_time)
    d2 = handler.handle(cmd, fixed_id, fixed_time)

    # Strict equality check
    assert d1 == d2
    assert d1.id == fixed_id
    assert d1.issued_at == fixed_time
    assert d1.action == cmd.action
    assert d1.scope == cmd.scope
    assert d1.effect["mode"] == "SILENT"


def test_escalation_approval():
    handler = StaticAdminCommandHandler()
    cmd = AdminCommand(
        id=uuid4(),
        action=GovernanceAction.APPROVE,
        scope=GovernanceScope.ESCALATION,
        target_id="escalation_abc"
    )

    fixed_id = uuid4()
    fixed_time = datetime.utcnow()

    decision = handler.handle(cmd, fixed_id, fixed_time)

    assert decision.action == GovernanceAction.APPROVE
    assert decision.effect["target_id"] == "escalation_abc"