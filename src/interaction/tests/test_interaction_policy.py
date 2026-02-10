import pytest
from uuid import uuid4
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.interaction.domain.envelope import InteractionEnvelope, TargetHint, PriorityHint, Visibility
from src.interaction.domain.policy_decision import PolicyDecision
from src.interaction.services.policy_engine import StandardInteractionPolicy
from src.core.config.runtime_profile import RuntimeProfile, Environment, SafetyLimits


# --- Helpers ---

def create_envelope(visibility: Visibility, target: TargetHint) -> InteractionEnvelope:
    intent = InteractionIntent(uuid4(), InteractionType.MESSAGE, "test", {})
    return InteractionEnvelope(intent, target, PriorityHint.NORMAL, visibility)


def create_profile(env: Environment, allow_exec: bool) -> RuntimeProfile:
    return RuntimeProfile(
        env=env,
        limits=SafetyLimits(),
        allow_execution=allow_exec
    )


# --- Tests ---

def test_policy_determinism():
    policy = StandardInteractionPolicy()
    envelope = create_envelope(Visibility.EXTERNAL, TargetHint.USER)
    profile = create_profile(Environment.PROD, True)

    d1 = policy.evaluate(envelope, profile)
    d2 = policy.evaluate(envelope, profile)

    assert d1 == d2
    assert d1.allowed == d2.allowed


def test_execution_disabled_block():
    policy = StandardInteractionPolicy()
    envelope = create_envelope(Visibility.EXTERNAL, TargetHint.USER)
    # Profile with execution disabled
    profile = create_profile(Environment.PROD, False)

    decision = policy.evaluate(envelope, profile)

    assert not decision.allowed
    assert "Execution disabled" in decision.reason


def test_replay_isolation():
    policy = StandardInteractionPolicy()
    envelope = create_envelope(Visibility.EXTERNAL, TargetHint.USER)
    # Replay profile (even if allow_execution=True locally, env check should block)
    # Note: RuntimeProfile.replay() factory sets allow_execution=False by default,
    # but we test the env check logic specifically here.
    profile = create_profile(Environment.REPLAY, True)

    decision = policy.evaluate(envelope, profile)

    assert not decision.allowed
    assert "REPLAY mode" in decision.reason


def test_unknown_target_block():
    policy = StandardInteractionPolicy()
    envelope = create_envelope(Visibility.INTERNAL, TargetHint.UNKNOWN)
    profile = create_profile(Environment.DEV, True)

    decision = policy.evaluate(envelope, profile)

    assert not decision.allowed
    assert "Target unknown" in decision.reason


def test_broadcast_constraints():
    policy = StandardInteractionPolicy()
    envelope = create_envelope(Visibility.EXTERNAL, TargetHint.BROADCAST)
    profile = create_profile(Environment.PROD, True)

    decision = policy.evaluate(envelope, profile)

    assert decision.allowed
    assert "rate_limit_strict" in decision.constraints