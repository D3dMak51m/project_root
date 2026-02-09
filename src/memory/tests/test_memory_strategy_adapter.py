import pytest
from src.memory.domain.memory_signal import MemorySignal
from src.memory.services.memory_strategy_adapter import MemoryStrategyAdapter


def test_adapter_determinism():
    adapter = MemoryStrategyAdapter()
    signal = MemorySignal(
        failure_pressure=1.0,
        recent_success=True,
        instability_detected=False,
        governance_suppressed_ratio=0.0
    )

    ctx1 = adapter.adapt(signal)
    ctx2 = adapter.adapt(signal)

    assert ctx1 == ctx2


def test_high_failure_pressure():
    adapter = MemoryStrategyAdapter()
    signal = MemorySignal(
        failure_pressure=3.0,  # High
        recent_success=False,
        instability_detected=False,
        governance_suppressed_ratio=0.0
    )

    ctx = adapter.adapt(signal)

    assert ctx.risk_bias == -0.5  # Averse
    assert ctx.priority_modifier < 1.0  # Dampened


def test_instability_cooldown():
    adapter = MemoryStrategyAdapter()
    signal = MemorySignal(
        failure_pressure=0.0,
        recent_success=False,
        instability_detected=True,
        governance_suppressed_ratio=0.0
    )

    ctx = adapter.adapt(signal)

    assert ctx.cooldown_required is True
    assert ctx.exploration_suppressed is True


def test_success_boost():
    adapter = MemoryStrategyAdapter()
    signal = MemorySignal(
        failure_pressure=0.0,
        recent_success=True,
        instability_detected=False,
        governance_suppressed_ratio=0.0
    )

    ctx = adapter.adapt(signal)

    assert ctx.risk_bias > 0.0  # Seeking
    assert ctx.priority_modifier > 1.0  # Boosted


def test_governance_suppression():
    adapter = MemoryStrategyAdapter()
    signal = MemorySignal(
        failure_pressure=0.0,
        recent_success=False,
        instability_detected=False,
        governance_suppressed_ratio=0.5  # High
    )

    ctx = adapter.adapt(signal)

    assert ctx.exploration_suppressed is True