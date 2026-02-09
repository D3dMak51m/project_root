import pytest
from src.memory.domain.strategic_learning_signal import StrategicLearningSignal
from src.memory.domain.meta_learning_policy import MetaLearningPolicy
from src.memory.domain.meta_learning_context import MetaLearningContext
from src.memory.services.meta_learning_resolver import MetaLearningResolver


def create_signal(bias: float = 0.2) -> StrategicLearningSignal:
    return StrategicLearningSignal(
        avoid_risk_patterns=True,
        reduce_exploration=True,
        policy_pressure_high=False,
        governance_deadlock_detected=False,
        long_term_priority_bias=bias
    )


def test_learning_disabled():
    resolver = MetaLearningResolver()
    policy = MetaLearningPolicy(learning_enabled=False)
    context = MetaLearningContext(policy, False, True, 100)
    signal = create_signal()

    result = resolver.resolve(signal, context)

    assert result.long_term_priority_bias == 0.0
    assert not result.avoid_risk_patterns


def test_governance_lock_blocks_learning():
    resolver = MetaLearningResolver()
    policy = MetaLearningPolicy(learning_enabled=True)
    context = MetaLearningContext(policy, is_governance_locked=True, is_system_stable=True,
                                  ticks_since_last_failure=100)
    signal = create_signal()

    result = resolver.resolve(signal, context)

    assert result.long_term_priority_bias == 0.0


def test_cooldown_blocks_learning():
    resolver = MetaLearningResolver()
    policy = MetaLearningPolicy(cooldown_ticks_after_failure=10)
    context = MetaLearningContext(policy, False, True, ticks_since_last_failure=5)  # < 10
    signal = create_signal()

    result = resolver.resolve(signal, context)

    assert result.long_term_priority_bias == 0.0


def test_bias_clamping():
    resolver = MetaLearningResolver()
    policy = MetaLearningPolicy(max_learning_delta_per_tick=0.1)
    context = MetaLearningContext(policy, False, True, 100)
    signal = create_signal(bias=0.5)  # > 0.1

    result = resolver.resolve(signal, context)

    assert result.long_term_priority_bias == 0.1  # Clamped
    assert result.avoid_risk_patterns  # Flags preserved


def test_stability_requirement():
    resolver = MetaLearningResolver()
    policy = MetaLearningPolicy(require_stability_for_learning=True)
    context = MetaLearningContext(policy, False, is_system_stable=False, ticks_since_last_failure=100)
    signal = create_signal()

    result = resolver.resolve(signal, context)

    assert result.long_term_priority_bias == 0.0