import pytest
from uuid import uuid4
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.autonomy.services.autonomy_state_evaluator import StandardAutonomyStateEvaluator
from src.interaction.domain.envelope import InteractionEnvelope, TargetHint, PriorityHint, Visibility
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile, Environment, SafetyLimits


# --- Helpers ---

def create_envelope(priority: PriorityHint = PriorityHint.NORMAL) -> InteractionEnvelope:
    intent = InteractionIntent(uuid4(), InteractionType.MESSAGE, "test", {})
    return InteractionEnvelope(intent, TargetHint.USER, priority, Visibility.EXTERNAL)


def create_profile() -> RuntimeProfile:
    return RuntimeProfile(Environment.PROD, SafetyLimits())


# --- Tests ---

def test_evaluator_determinism():
    evaluator = StandardAutonomyStateEvaluator()
    envelope = create_envelope()
    policy = PolicyDecision(True, "OK", [])
    profile = create_profile()

    s1 = evaluator.evaluate(envelope, policy, profile)
    s2 = evaluator.evaluate(envelope, policy, profile)

    assert s1 == s2
    assert s1.mode == s2.mode


def test_policy_blocked():
    evaluator = StandardAutonomyStateEvaluator()
    envelope = create_envelope()
    policy = PolicyDecision(False, "Blocked", [])
    profile = create_profile()

    state = evaluator.evaluate(envelope, policy, profile)

    assert state.mode == AutonomyMode.BLOCKED
    assert state.pressure_level == 0.0
    assert not state.requires_human


def test_escalation_required():
    evaluator = StandardAutonomyStateEvaluator()
    envelope = create_envelope()
    policy = PolicyDecision(True, "OK", ["requires_approval"])
    profile = create_profile()

    state = evaluator.evaluate(envelope, policy, profile)

    assert state.mode == AutonomyMode.ESCALATION_REQUIRED
    assert state.requires_human
    assert state.pressure_level == 0.7


def test_low_priority_silence():
    evaluator = StandardAutonomyStateEvaluator()
    envelope = create_envelope(priority=PriorityHint.LOW)
    policy = PolicyDecision(True, "OK", [])
    profile = create_profile()

    state = evaluator.evaluate(envelope, policy, profile)

    assert state.mode == AutonomyMode.SILENT
    assert state.pressure_level == 0.1


def test_ready_state():
    evaluator = StandardAutonomyStateEvaluator()
    envelope = create_envelope(priority=PriorityHint.NORMAL)
    policy = PolicyDecision(True, "OK", [])
    profile = create_profile()

    state = evaluator.evaluate(envelope, policy, profile)

    assert state.mode == AutonomyMode.READY
    assert state.pressure_level == 0.5
    assert not state.requires_human


def test_replay_safety():
    evaluator = StandardAutonomyStateEvaluator()
    envelope = create_envelope()
    policy = PolicyDecision(True, "OK", [])
    # Replay profile should not change logic (logic depends on policy/envelope)
    profile = RuntimeProfile(Environment.REPLAY, SafetyLimits())

    state = evaluator.evaluate(envelope, policy, profile)

    assert state.mode == AutonomyMode.READY