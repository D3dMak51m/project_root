from typing import List
from src.world.interfaces.cognitive_feed import CognitiveFeed
from src.world.domain.signal import NormalizedSignal
from src.world.domain.observation import WorldObservation
from src.world.interfaces.salience_analyzer import SalienceAnalyzer
from src.world.interfaces.trend_detector import TrendDetector
from src.world.interfaces.target_resolver import TargetResolver
from src.world.interfaces.signal_store import SignalStore


class StandardCognitiveFeed(CognitiveFeed):
    """
    Deterministic implementation of CognitiveFeed.
    Orchestrates analyzers to enrich signals.
    """

    def __init__(
            self,
            salience_analyzer: SalienceAnalyzer,
            trend_detector: TrendDetector,
            target_resolver: TargetResolver,
            signal_store: SignalStore
    ):
        self.salience_analyzer = salience_analyzer
        self.trend_detector = trend_detector
        self.target_resolver = target_resolver
        self.signal_store = signal_store

        # Internal state for trend windows (in a real system, this might be persisted separately)
        # For I.4 scope, we keep it in memory or assume it's passed.
        # To keep it pure, we might need to fetch history.
        # Here we assume trend detector manages its state or we rebuild it.
        # For simplicity and determinism in this stage, we'll fetch history for salience.
        self._trend_windows = []

    def build(self, signals: List[NormalizedSignal]) -> List[WorldObservation]:
        observations = []

        # Fetch history for salience context
        # In production, this would be optimized (e.g., last N signals)
        history = self.signal_store.list()

        for signal in signals:
            # 1. Calculate Salience
            salience = self.salience_analyzer.evaluate(signal, history)

            # 2. Update Trends
            # Note: This updates the internal window state for the feed sequence
            self._trend_windows = self.trend_detector.update(signal, self._trend_windows)
            # We snapshot the current windows relevant to this signal
            # (In reality, we might filter relevant windows, here we attach all active)
            current_trends = list(self._trend_windows)

            # 3. Resolve Targets
            targets = self.target_resolver.resolve(signal)

            # 4. Aggregate
            observation = WorldObservation(
                signal=signal,
                salience=salience,
                trends=current_trends,
                targets=targets
            )
            observations.append(observation)

            # Update history for next iteration in this batch (causality)
            history.append(signal)

        return observations