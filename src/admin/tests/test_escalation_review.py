import pytest
from uuid import uuid4
from datetime import datetime
from src.admin.domain.governance_action import GovernanceAction
from src.admin.domain.governance_scope import GovernanceScope
from src.admin.services.escalation_review_service import StandardEscalationReviewService
from src.admin.services.admin_gateway import StandardAdminGateway
from src.admin.services.governance_service import StandardGovernanceService
from src.admin.services.admin_command_handler import StaticAdminCommandHandler
from src.admin.store.governance_state_store import GovernanceStateStore
from src.admin.store.audit_log_store import AuditLogStore
from src.admin.tests.test_governance_service import FixedTimeSource, FixedIdSource


@pytest.fixture
def review_service():
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
    return StandardEscalationReviewService(gateway)


def test_approve_escalation(review_service):
    decision = review_service.approve_escalation("esc_123", "Looks good")

    assert decision.action == GovernanceAction.APPROVE
    assert decision.scope == GovernanceScope.ESCALATION
    assert decision.effect["target_id"] == "esc_123"
    assert decision.effect["reason"] == "Looks good"
    # Decision ID/Time come from GovernanceService
    assert decision.id is not None
    assert decision.issued_at is not None


def test_reject_escalation(review_service):
    decision = review_service.reject_escalation("esc_456", "Too risky")

    assert decision.action == GovernanceAction.REJECT
    assert decision.scope == GovernanceScope.ESCALATION
    assert decision.effect["target_id"] == "esc_456"