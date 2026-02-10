import pytest
from uuid import uuid4
from datetime import datetime, timezone
from typing import List

from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import SignalSalience, TrendWindow
from src.world.domain.target import TargetBinding
from src.world.services.cognitive_feed import StandardCognitiveFeed
from src.world.interfaces.salience_analyzer import SalienceAnalyzer
from src.world.interfaces.trend_detector import TrendDetector
from src.world.interfaces.target_resolver import TargetResolver
from src.world.interfaces.signal_store import SignalStore


# --- Mocks ---

class MockSalienceAnalyzer(SalienceAnalyzer):
    def evaluate(self, signal, history):
        return SignalSalience(signal.signal_id, "src", signal.received_at, 0.5, 0.5, 0.5, 0.5)


class MockTrendDetector(TrendDetector):
    def update(self, signal, windows):
        return [TrendWindow("key", signal.received_at, signal.received_at, 1, 0.0)]


class MockTargetResolver(TargetResolver):
    def resolve(self, signal):
        return TargetBinding(signal.signal_id, None, None, [])


class MockSignalStore(SignalStore):
    def append(self, signal): pass

    def list(self, since=None): return []


# --- Tests ---

def create_signal() -> NormalizedSignal:
    return NormalizedSignal(
        signal_id=uuid4(),
        source_id="test",
        received_at=datetime.now(timezone.utc),
        observed_at=datetime.now(timezone.utc),
        content="test content",
        metadata={}
    )


def test_feed_construction():
    feed = StandardCognitiveFeed(
        MockSalienceAnalyzer(),
        MockTrendDetector(),
        MockTargetResolver(),
        MockSignalStore()
    )

    signals = [create_signal(), create_signal()]
    observations = feed.build(signals)

    assert len(observations) == 2
    assert observations[0].signal == signals[0]
    assert isinstance(observations[0].salience, SignalSalience)
    assert isinstance(observations[0].targets, TargetBinding)
    assert len(observations[0].trends) > 0


def test_feed_determinism():
    feed = StandardCognitiveFeed(
        MockSalienceAnalyzer(),
        MockTrendDetector(),
        MockTargetResolver(),
        MockSignalStore()
    )

    sig = create_signal()
    obs1 = feed.build([sig])

    # Reset internal state for fair comparison if needed,
    # but for same input instance it should be identical if pure.
    # Re-instantiate to clear internal state
    feed2 = StandardCognitiveFeed(
        MockSalienceAnalyzer(),
        MockTrendDetector(),
        MockTargetResolver(),
        MockSignalStore()
    )
    obs2 = feed2.build([sig])

    # Compare relevant fields (excluding object identity if mocks return new instances)
    # Since mocks return new instances, we compare values
    assert obs1[0].signal == obs2[0].signal
    assert obs1[0].salience == obs2[0].salience