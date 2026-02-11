import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.memory.domain.event_record import EventRecord
from src.memory.domain.governance_snapshot import GovernanceSnapshot
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.services.memory_decay_policy import LinearDecay, ExponentialDecay
from src.memory.services.temporal_memory_analyzer import TemporalMemoryAnalyzer
from src.memory.services.memory_signal_builder import MemorySignalBuilder
from src.memory.domain.temporal_window import TemporalWindow

# --- Helpers ---

FIXED_NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def create_event(status: ExecutionStatus, time_offset_seconds: int = 0, gov_locked: bool = False) -> EventRecord:
    return EventRecord(
        id=uuid4(),
        intent_id=uuid4(),
        execution_status=status,
        execution_result=ExecutionResult(status, FIXED_NOW, failure_type=ExecutionFailureType.NONE),
        autonomy_state_before=AutonomyState(AutonomyMode.READY, "test", 0.5, [], False),
        policy_decision=PolicyDecision(True, "OK", []),
        governance_snapshot=GovernanceSnapshot(gov_locked, False, gov_locked),
        issued_at=FIXED_NOW - timedelta(seconds=time_offset_seconds),
        context_domain="test"
    )


# --- Tests ---

def test_linear_decay():
    strategy = LinearDecay(max_age_seconds=100)
    assert strategy.decay(timedelta(seconds=0)) == 1.0
    assert strategy.decay(timedelta(seconds=50)) == 0.5
    assert strategy.decay(timedelta(seconds=100)) == 0.0
    assert strategy.decay(timedelta(seconds=200)) == 0.0


def test_exponential_decay():
    strategy = ExponentialDecay(half_life_seconds=10)
    assert strategy.decay(timedelta(seconds=0)) == 1.0
    assert strategy.decay(timedelta(seconds=10)) == 0.5
    assert strategy.decay(timedelta(seconds=20)) == 0.25


def test_temporal_analyzer_weighting():
    analyzer = TemporalMemoryAnalyzer(LinearDecay(100))

    # Recent success
    e1 = create_event(ExecutionStatus.SUCCESS, 0)
    # Old failure (decayed to 0)
    e2 = create_event(ExecutionStatus.FAILED, 200)
    # Recent failure with governance lock
    e3 = create_event(ExecutionStatus.FAILED, 10, gov_locked=True)

    weighted = analyzer.analyze([e1, e2, e3], FIXED_NOW)

    # Sorted by time: e2 (oldest), e3, e1 (newest)
    # e2: age 200s -> decay 0.0 -> weight 0.0
    assert weighted[0].event == e2
    assert weighted[0].weight == 0.0
    assert weighted[0].window == TemporalWindow.RECENT  # 200s < 3600s

    # e3: age 10s -> decay 0.9. Gov locked -> mod 0.2 (exec locked) * 0.4 (auto locked) = 0.08
    # Density: e2 was failure, e3 is failure -> consecutive=2 -> mod 1.5
    # Weight: -1.0 * 0.9 * 0.08 * 1.5 = -0.108
    assert weighted[1].event == e3
    assert weighted[1].weight < 0
    assert abs(weighted[1].weight) < 0.2

    # e1: age 0s -> decay 1.0. Success -> reset density.
    # Weight: 1.0 * 1.0 * 1.0 * 1.0 = 1.0
    assert weighted[2].event == e1
    assert weighted[2].weight == 1.0
    assert weighted[2].window == TemporalWindow.IMMEDIATE


def test_signal_builder():
    analyzer = TemporalMemoryAnalyzer(LinearDecay(100))
    builder = MemorySignalBuilder()

    # 3 recent failures -> instability
    # Sorted: e3 (30s), e2 (20s), e1 (10s)
    events = [
        create_event(ExecutionStatus.FAILED, 10),
        create_event(ExecutionStatus.FAILED, 20),
        create_event(ExecutionStatus.REJECTED, 30)
    ]

    weighted = analyzer.analyze(events, FIXED_NOW)
    # Weights:
    # e3 (30s): -1.5 * 0.7 * 1.0 * 1.0 = -1.05
    # e2 (20s): -1.0 * 0.8 * 1.0 * 1.5 = -1.2
    # e1 (10s): -1.0 * 0.9 * 1.0 * 2.0 = -1.8
    # Sum abs negative: 1.05 + 1.2 + 1.8 = 4.05 > 2.5 (Threshold)

    signal = builder.build(weighted, analyzer, {})

    assert signal.instability_detected is True
    assert signal.recent_success is False
    assert signal.failure_pressure > 0
    assert signal.governance_suppressed_ratio == 0.0


def test_governance_ratio():
    analyzer = TemporalMemoryAnalyzer(LinearDecay(100))
    builder = MemorySignalBuilder()

    events = [
        create_event(ExecutionStatus.FAILED, 10, gov_locked=True),
        create_event(ExecutionStatus.SUCCESS, 20, gov_locked=False)
    ]

    weighted = analyzer.analyze(events, FIXED_NOW)
    signal = builder.build(weighted, analyzer, {})

    # 1 out of 2 recent events suppressed
    assert signal.governance_suppressed_ratio == 0.5
