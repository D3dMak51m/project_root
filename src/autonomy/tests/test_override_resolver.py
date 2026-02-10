import pytest
from src.autonomy.domain.escalation_decision import EscalationDecision
from src.autonomy.domain.human_override_decision import HumanOverrideDecision
from src.autonomy.domain.final_execution_decision import FinalExecutionDecision
from src.autonomy.services.override_resolver import StandardOverrideResolver


def test_resolver_determinism():
    resolver = StandardOverrideResolver()

    d1 = resolver.resolve(EscalationDecision.ESCALATE_TO_HUMAN, HumanOverrideDecision.APPROVE)
    d2 = resolver.resolve(EscalationDecision.ESCALATE_TO_HUMAN, HumanOverrideDecision.APPROVE)

    assert d1 == d2
    assert d1 == FinalExecutionDecision.EXECUTE


def test_drop_propagation():
    resolver = StandardOverrideResolver()
    # Even with approval, DROP escalation must result in DROP (though logically shouldn't happen together)
    # The resolver logic prioritizes escalation status first.
    decision = resolver.resolve(EscalationDecision.DROP, HumanOverrideDecision.APPROVE)
    assert decision == FinalExecutionDecision.DROP

    decision_none = resolver.resolve(EscalationDecision.DROP, None)
    assert decision_none == FinalExecutionDecision.DROP


def test_execute_propagation():
    resolver = StandardOverrideResolver()
    decision = resolver.resolve(EscalationDecision.EXECUTE, None)
    assert decision == FinalExecutionDecision.EXECUTE


def test_escalation_pending():
    resolver = StandardOverrideResolver()
    decision = resolver.resolve(EscalationDecision.ESCALATE_TO_HUMAN, None)
    assert decision is None


def test_escalation_approve():
    resolver = StandardOverrideResolver()
    decision = resolver.resolve(EscalationDecision.ESCALATE_TO_HUMAN, HumanOverrideDecision.APPROVE)
    assert decision == FinalExecutionDecision.EXECUTE


def test_escalation_reject():
    resolver = StandardOverrideResolver()
    decision = resolver.resolve(EscalationDecision.ESCALATE_TO_HUMAN, HumanOverrideDecision.REJECT)
    assert decision == FinalExecutionDecision.DROP