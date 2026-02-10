from typing import List, Dict, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.memory.domain.event_record import EventRecord
from src.core.domain.execution_result import ExecutionStatus
from src.memory.interfaces.memory_decay_strategy import MemoryDecayStrategy
from src.memory.domain.temporal_window import TemporalWindow, classify_window


@dataclass(frozen=True)
class WeightedEvent:
    event: EventRecord
    weight: float
    window: TemporalWindow


class TemporalMemoryAnalyzer:
    """
    Analyzes a list of events to compute weights, detect clusters, and classify windows.
    Pure service.
    """

    # Threshold for weighted failure sum to consider it a cluster
    FAILURE_CLUSTER_THRESHOLD = 2.5

    def __init__(self, decay_strategy: MemoryDecayStrategy):
        self.decay_strategy = decay_strategy

    def analyze(self, events: List[EventRecord], now: datetime) -> List[WeightedEvent]:
        weighted_events = []

        # 1. Sort events by time (Oldest to Newest) to correctly calculate density
        sorted_events = sorted(events, key=lambda e: e.issued_at)

        consecutive_failures = 0

        for event in sorted_events:
            age = now - event.issued_at
            if age.total_seconds() < 0:
                decay_factor = 1.0
            else:
                decay_factor = self.decay_strategy.decay(age)

            # Base weight from status
            base_weight = 0.0
            is_failure = False

            if event.execution_status == ExecutionStatus.SUCCESS:
                base_weight = 1.0
                consecutive_failures = 0  # Reset density
            elif event.execution_status == ExecutionStatus.FAILED:
                base_weight = -1.0
                is_failure = True
            elif event.execution_status == ExecutionStatus.REJECTED:
                base_weight = -1.5
                is_failure = True

            # Density modifier calculation
            density_mod = 1.0
            if is_failure:
                consecutive_failures += 1
                # Boost weight for repeated failures: 1.0, 1.5, 2.0, etc.
                density_mod = 1.0 + (0.5 * max(0, consecutive_failures - 1))

            # Governance modifier
            gov_mod = 1.0
            if event.governance_snapshot.is_execution_locked:
                gov_mod *= 0.2
            if event.governance_snapshot.is_autonomy_locked:
                gov_mod *= 0.4

            final_weight = base_weight * decay_factor * gov_mod * density_mod

            window = classify_window(event, now)

            weighted_events.append(WeightedEvent(event, final_weight, window))

        return weighted_events

    def detect_failure_clusters(self, weighted_events: List[WeightedEvent]) -> bool:
        """
        Detects if there is a cluster of recent failures using weighted sum.
        Considers only IMMEDIATE and RECENT windows.
        """
        weighted_failure_sum = sum(
            abs(we.weight)
            for we in weighted_events
            if we.weight < 0 and we.window in (TemporalWindow.IMMEDIATE, TemporalWindow.RECENT)
        )

        return weighted_failure_sum >= self.FAILURE_CLUSTER_THRESHOLD