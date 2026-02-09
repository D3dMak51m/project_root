from typing import List
from src.memory.domain.memory_signal import MemorySignal
from src.memory.services.temporal_memory_analyzer import WeightedEvent, TemporalMemoryAnalyzer
from src.memory.domain.temporal_window import TemporalWindow
from src.core.domain.execution_result import ExecutionStatus


class MemorySignalBuilder:
    """
    Builds a MemorySignal from analyzed weighted events.
    """

    def build(self, weighted_events: List[WeightedEvent], analyzer: TemporalMemoryAnalyzer) -> MemorySignal:

        # 1. Failure Pressure
        # Sum of negative weights (failures/rejections)
        failure_pressure = sum(
            abs(we.weight) for we in weighted_events
            if we.weight < 0
        )

        # 2. Recent Success
        recent_success = any(
            we.event.execution_status == ExecutionStatus.SUCCESS
            for we in weighted_events
            if we.window in (TemporalWindow.IMMEDIATE, TemporalWindow.RECENT)
        )

        # 3. Instability
        instability = analyzer.detect_failure_clusters(weighted_events)

        # 4. Governance Suppressed Ratio
        # Count events where governance was locked vs total events in recent history
        recent_events = [we for we in weighted_events if we.window in (TemporalWindow.IMMEDIATE, TemporalWindow.RECENT)]
        total_recent = len(recent_events)

        if total_recent == 0:
            gov_ratio = 0.0
        else:
            suppressed_count = sum(
                1 for we in recent_events
                if we.event.governance_snapshot.is_execution_locked or we.event.governance_snapshot.is_autonomy_locked
            )
            gov_ratio = suppressed_count / total_recent

        return MemorySignal(
            failure_pressure=failure_pressure,
            recent_success=recent_success,
            instability_detected=instability,
            governance_suppressed_ratio=gov_ratio
        )