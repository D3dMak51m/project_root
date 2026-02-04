import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from src.world.domain.signal import NormalizedSignal
from src.world.services.salience_analysis import BasicSalienceAnalyzer
from src.world.services.trend_detection import RollingWindowTrendDetector
from src.world.domain.salience import TrendWindow


def create_signal(content: str, time_offset: int = 0) -> NormalizedSignal:
    return NormalizedSignal(
        signal_id=uuid4(),
        source_id="test_src",
        received_at=datetime.now(timezone.utc) + timedelta(seconds=time_offset),
        observed_at=datetime.now(timezone.utc),
        content=content,
        metadata={}
    )


def test_salience_determinism():
    analyzer = BasicSalienceAnalyzer()
    sig = create_signal("test")
    history = [create_signal("test"), create_signal("other")]

    res1 = analyzer.evaluate(sig, history)
    res2 = analyzer.evaluate(sig, history)

    assert res1 == res2
    assert 0.0 <= res1.salience_score <= 1.0


def test_salience_metrics():
    analyzer = BasicSalienceAnalyzer()
    sig = create_signal("repeat")
    # History with 5 repeats
    history = [create_signal("repeat") for _ in range(5)]

    res = analyzer.evaluate(sig, history)

    # Frequency should be 0.5 (5/10)
    assert res.frequency_score == 0.5
    # Novelty should be 0.5
    assert res.novelty_score == 0.5


def test_trend_update():
    detector = RollingWindowTrendDetector(window_size_seconds=60)
    sig1 = create_signal("trend", 0)
    sig2 = create_signal("trend", 10)

    # Initial state
    windows = detector.update(sig1, [])
    assert len(windows) == 1
    assert windows[0].count == 1

    # Update with second signal
    windows_v2 = detector.update(sig2, windows)
    assert len(windows_v2) == 1
    assert windows_v2[0].count == 2
    assert windows_v2[0].delta > 0


def test_trend_expiration():
    detector = RollingWindowTrendDetector(window_size_seconds=10)
    sig1 = create_signal("trend", 0)
    sig2 = create_signal("trend", 20)  # Outside window

    windows = detector.update(sig1, [])
    windows_v2 = detector.update(sig2, windows)

    # Should have 2 windows now (one expired, one new)
    assert len(windows_v2) == 2
    assert windows_v2[0].count == 1  # Old window unchanged
    assert windows_v2[1].count == 1  # New window started