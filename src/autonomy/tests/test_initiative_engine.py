import pytest
from uuid import uuid4
from src.autonomy.domain.initiative_decision import InitiativeDecision
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.services.initiative_engine import StandardInitiativeEngine
from src.interaction.domain.envelope import InteractionEnvelope, TargetHint, PriorityHint, Visibility
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile, Environment, SafetyLimits


# --- Helpers ---

def create_envelope(priority: PriorityHint = PriorityHint.NORMAL) -> InteractionEnvelope:
    intent = InteractionIntent(uuid4(), InteractionType.MESSAGE, "test", {})
    return InteractionEnvelope(intent, TargetHint.USER, priority, Visibility.EXTERNAL)


def create_profile(env: Environment = Environment.PROD) -> RuntimeProfile:
    return RuntimeProfile(env, SafetyLimits())


def create_autonomy(mode: AutonomyMode, pressure: float = 0.5, requires_human: bool = False) -> AutonomyState:
    return AutonomyState(mode, "test", pressure, [], requires_human)


# --- Tests ---

def test_determinism():
    engine = StandardInitiativeEngine()
    envelope = create_envelope()
    policy = PolicyDecision(True, "OK", [])
    autonomy = create_autonomy(AutonomyMode.READY)
    profile = create_profile()

    d1 = engine.evaluate(envelope, policy, autonomy, profile)
    d2 = engine.evaluate(envelope, policy, autonomy, profile)

    assert d1 == d2


def test_hold_on_blocked_mode():
    engine = StandardInitiativeEngine()
    envelope = create_envelope(PriorityHint.HIGH)
    policy = PolicyDecision(True, "OK", [])
    autonomy = create_autonomy(AutonomyMode.BLOCKED)
    profile = create_profile()

    decision = engine.evaluate(envelope, policy, autonomy, profile)
    assert decision == InitiativeDecision.HOLD


def test_hold_on_policy_denied():
    engine = StandardInitiativeEngine()
    envelope = create_envelope(PriorityHint.HIGH)
    policy = PolicyDecision(False, "Denied", [])
    autonomy = create_autonomy(AutonomyMode.READY)
    profile = create_profile()

    decision = engine.evaluate(envelope, policy, autonomy, profile)
    assert decision == InitiativeDecision.HOLD


def test_defer_on_requires_human():
    engine = StandardInitiativeEngine()
    envelope = create_envelope()
    policy = PolicyDecision(True, "OK", [])
    # Case 1: Mode is ESCALATION_REQUIRED
    autonomy1 = create_autonomy(AutonomyMode.ESCALATION_REQUIRED, requires_human=True)
    # Case 2: Mode is READY but flag is True (should not happen in valid state, but logic handles it)
    autonomy2 = create_autonomy(AutonomyMode.READY, requires_human=True)
    profile = create_profile()

    assert engine.evaluate(envelope, policy, autonomy1, profile) == InitiativeDecision.DEFER
    assert engine.evaluate(envelope, policy, autonomy2, profile) == InitiativeDecision.DEFER


def test_initiate_on_ready_high():
    engine = StandardInitiativeEngine()
    envelope = create_envelope(PriorityHint.HIGH)
    policy = PolicyDecision(True, "OK", [])
    autonomy = create_autonomy(AutonomyMode.READY)
    profile = create_profile()

    decision = engine.evaluate(envelope, policy, autonomy, profile)
    assert decision == InitiativeDecision.INITIATE


def test_initiate_on_ready_normal_pressure():
    engine = StandardInitiativeEngine()
    envelope = create_envelope(PriorityHint.NORMAL)
    policy = PolicyDecision(True, "OK", [])
    # Pressure >= 0.5
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.5)
    profile = create_profile()

    decision = engine.evaluate(envelope, policy, autonomy, profile)
    assert decision == InitiativeDecision.INITIATE


def test_hold_on_ready_normal_low_pressure():
    engine = StandardInitiativeEngine()
    envelope = create_envelope(PriorityHint.NORMAL)
    policy = PolicyDecision(True, "OK", [])
    # Pressure < 0.5
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.4)
    profile = create_profile()

    decision = engine.evaluate(envelope, policy, autonomy, profile)
    assert decision == InitiativeDecision.HOLD


def test_hold_on_ready_low_priority():
    engine = StandardInitiativeEngine()
    envelope = create_envelope(PriorityHint.LOW)
    policy = PolicyDecision(True, "OK", [])
    autonomy = create_autonomy(AutonomyMode.READY, pressure=1.0)  # Even high pressure won't force low priority
    profile = create_profile()

    decision = engine.evaluate(envelope, policy, autonomy, profile)
    assert decision == InitiativeDecision.HOLD


def test_replay_safety():
    engine = StandardInitiativeEngine()
    envelope = create_envelope(PriorityHint.HIGH)
    policy = PolicyDecision(True, "OK", [])
    autonomy = create_autonomy(AutonomyMode.READY)
    profile = create_profile(Environment.REPLAY)

    # Logic should be identical regardless of profile env
    decision = engine.evaluate(envelope, policy, autonomy, profile)
    assert decision == InitiativeDecision.INITIATE