import pytest
from src.autonomy.domain.escalation_decision import EscalationDecision
from src.autonomy.domain.silence_decision import SilenceDecision
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.autonomy.services.escalation_evaluator import StandardEscalationEvaluator
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile, Environment, SafetyLimits


# --- Helpers ---

def create_profile() -> RuntimeProfile:
    return RuntimeProfile(Environment.PROD, SafetyLimits())


def create_autonomy(requires_human: bool = False) -> AutonomyState:
    return AutonomyState(AutonomyMode.READY, "test", 0.5, [], requires_human)


def create_policy(constraints=None) -> PolicyDecision:
    return PolicyDecision(True, "OK", constraints or [])


# --- Tests ---

def test_evaluator_determinism():
    evaluator = StandardEscalationEvaluator()
    silence = SilenceDecision.ALLOW
    autonomy = create_autonomy()
    policy = create_policy()
    profile = create_profile()

    d1 = evaluator.evaluate(silence, autonomy, policy, profile)
    d2 = evaluator.evaluate(silence, autonomy, policy, profile)

    assert d1 == d2
    assert d1 == EscalationDecision.EXECUTE


def test_drop_on_silence():
    evaluator = StandardEscalationEvaluator()
    silence = SilenceDecision.SILENCE
    autonomy = create_autonomy()
    policy = create_policy()
    profile = create_profile()

    decision = evaluator.evaluate(silence, autonomy, policy, profile)
    assert decision == EscalationDecision.DROP


def test_escalate_on_requires_human():
    evaluator = StandardEscalationEvaluator()
    silence = SilenceDecision.ALLOW
    autonomy = create_autonomy(requires_human=True)
    policy = create_policy()
    profile = create_profile()

    decision = evaluator.evaluate(silence, autonomy, policy, profile)
    assert decision == EscalationDecision.ESCALATE_TO_HUMAN


def test_escalate_on_policy_constraint():
    evaluator = StandardEscalationEvaluator()
    silence = SilenceDecision.ALLOW
    autonomy = create_autonomy()
    profile = create_profile()

    triggers = ["requires_approval", "audit_logging", "high_risk"]

    for trigger in triggers:
        policy = create_policy(constraints=[trigger])
        decision = evaluator.evaluate(silence, autonomy, policy, profile)
        assert decision == EscalationDecision.ESCALATE_TO_HUMAN, f"Failed to escalate on {trigger}"


def test_execute_when_clean():
    evaluator = StandardEscalationEvaluator()
    silence = SilenceDecision.ALLOW
    autonomy = create_autonomy(requires_human=False)
    policy = create_policy(constraints=["safe_constraint"])  # Non-trigger constraint
    profile = create_profile()

    decision = evaluator.evaluate(silence, autonomy, policy, profile)
    assert decision == EscalationDecision.EXECUTE


def test_replay_safety():
    evaluator = StandardEscalationEvaluator()
    silence = SilenceDecision.ALLOW
    autonomy = create_autonomy()
    policy = create_policy()
    profile = RuntimeProfile(Environment.REPLAY, SafetyLimits())

    # Logic should be identical regardless of profile env
    decision = evaluator.evaluate(silence, autonomy, policy, profile)
    assert decision == EscalationDecision.EXECUTE