from typing import List
from src.world.interfaces.salience_analyzer import SalienceAnalyzer
from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import SignalSalience


class BasicSalienceAnalyzer(SalienceAnalyzer):
    """
    Deterministic analyzer using simple frequency and novelty heuristics.
    """

    def evaluate(
            self,
            signal: NormalizedSignal,
            history: List[NormalizedSignal]
    ) -> SignalSalience:
        # 1. Frequency Score (Repetition)
        # Count exact content matches in history
        matches = sum(1 for s in history if s.content == signal.content)
        # Normalize: 0 matches -> 0.0, 10+ matches -> 1.0
        frequency_score = min(1.0, matches / 10.0)

        # 2. Novelty Score (Uniqueness)
        # Inverse of frequency
        novelty_score = 1.0 - frequency_score

        # 3. Volume Score (Burst)
        # Count signals in the same short time window (e.g., last 1 hour)
        # Assuming history is sorted or we filter.
        # For pure function, we scan history.
        # Simplified: count signals from same source in history
        source_matches = sum(1 for s in history if s.source_id == signal.source_id)
        volume_score = min(1.0, source_matches / 20.0)

        # 4. Combined Salience
        # Weighted average
        salience_score = (frequency_score * 0.4) + (novelty_score * 0.4) + (volume_score * 0.2)

        return SignalSalience(
            signal_id=signal.signal_id,
            source_id=signal.source_id,
            timestamp=signal.received_at,
            frequency_score=frequency_score,
            novelty_score=novelty_score,
            volume_score=volume_score,
            salience_score=salience_score
        )