import pytest
from uuid import uuid4
from src.autonomy.domain.silence_decision import SilenceDecision
from src.autonomy.domain.silence_profile import SilenceProfile
from src.autonomy.domain.initiative_decision import InitiativeDecision
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.services.silence_evaluator import StandardSilenceEvaluator
from src.interaction.domain.envelope import InteractionEnvelope, TargetHint, PriorityHint, Visibility
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.core.config.runtime_profile import RuntimeProfile, Environment, SafetyLimits


# --- Helpers ---

def create_envelope(priority: PriorityHint = PriorityHint.NORMAL) -> InteractionEnvelope:
    intent = InteractionIntent(uuid4(), InteractionType.MESSAGE, "test", {})
    return InteractionEnvelope(intent, TargetHint.USER, priority, Visibility.EXTERNAL)


def create_profile() -> RuntimeProfile:
    return RuntimeProfile(Environment.PROD, SafetyLimits())


def create_autonomy(mode: AutonomyMode, pressure: float = 0.5) -> AutonomyState:
    return AutonomyState(mode, "test", pressure, [], False)


def create_silence_profile(base: float = 0.6, overrides=None) -> SilenceProfile:
    return SilenceProfile(base, overrides or {})


# --- Tests ---

def test_evaluator_determinism():
    evaluator = StandardSilenceEvaluator()
    envelope = create_envelope()
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.7)
    profile = create_profile()
    silence_profile = create_silence_profile(base=0.5)

    d1 = evaluator.evaluate(InitiativeDecision.INITIATE, envelope, autonomy, profile, silence_profile)
    d2 = evaluator.evaluate(InitiativeDecision.INITIATE, envelope, autonomy, profile, silence_profile)

    assert d1 == d2
    assert d1 == SilenceDecision.ALLOW


def test_silence_on_non_initiate():
    evaluator = StandardSilenceEvaluator()
    envelope = create_envelope()
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.9)  # High pressure
    profile = create_profile()
    silence_profile = create_silence_profile(base=0.1)  # Low threshold

    # Even with high pressure and low threshold, HOLD/DEFER must result in SILENCE
    assert evaluator.evaluate(InitiativeDecision.HOLD, envelope, autonomy, profile,
                              silence_profile) == SilenceDecision.SILENCE
    assert evaluator.evaluate(InitiativeDecision.DEFER, envelope, autonomy, profile,
                              silence_profile) == SilenceDecision.SILENCE


def test_silence_on_non_ready_mode():
    evaluator = StandardSilenceEvaluator()
    envelope = create_envelope()
    # Pressure > threshold, Initiative is INITIATE, but mode is not READY
    autonomy = create_autonomy(AutonomyMode.BLOCKED, pressure=0.9)
    profile = create_profile()
    silence_profile = create_silence_profile(base=0.5)

    # Note: InitiativeEngine usually returns HOLD if mode != READY, but SilenceEvaluator must enforce this invariant independently
    assert evaluator.evaluate(InitiativeDecision.INITIATE, envelope, autonomy, profile,
                              silence_profile) == SilenceDecision.SILENCE


def test_silence_below_threshold():
    evaluator = StandardSilenceEvaluator()
    envelope = create_envelope()
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.4)
    profile = create_profile()
    silence_profile = create_silence_profile(base=0.5)

    assert evaluator.evaluate(InitiativeDecision.INITIATE, envelope, autonomy, profile,
                              silence_profile) == SilenceDecision.SILENCE


def test_allow_above_threshold():
    evaluator = StandardSilenceEvaluator()
    envelope = create_envelope()
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.6)
    profile = create_profile()
    silence_profile = create_silence_profile(base=0.5)

    assert evaluator.evaluate(InitiativeDecision.INITIATE, envelope, autonomy, profile,
                              silence_profile) == SilenceDecision.ALLOW


def test_priority_override():
    evaluator = StandardSilenceEvaluator()
    envelope = create_envelope(PriorityHint.HIGH)
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.4)
    profile = create_profile()
    # Base is 0.5 (would silence), but HIGH override is 0.3 (should allow)
    silence_profile = create_silence_profile(base=0.5, overrides={PriorityHint.HIGH: 0.3})

    assert evaluator.evaluate(InitiativeDecision.INITIATE, envelope, autonomy, profile,
                              silence_profile) == SilenceDecision.ALLOW


def test_replay_safety():
    evaluator = StandardSilenceEvaluator()
    envelope = create_envelope()
    autonomy = create_autonomy(AutonomyMode.READY, pressure=0.6)
    profile = RuntimeProfile(Environment.REPLAY, SafetyLimits())
    silence_profile = create_silence_profile(base=0.5)

    # Logic should be identical in replay
    assert evaluator.evaluate(InitiativeDecision.INITIATE, envelope, autonomy, profile,
                              silence_profile) == SilenceDecision.ALLOW