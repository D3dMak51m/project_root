from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.core.domain.execution_intent import ExecutionIntent
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime


class StrategicArbitrator(ABC):
    """
    Resolves conflicts when multiple contexts produce ExecutionIntents simultaneously.
    Enforces global constraints and prioritization.
    """

    @abstractmethod
    def select(self, candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent]]) -> Optional[
        Tuple[StrategicContextRuntime, ExecutionIntent]]:
        pass


class PriorityArbitrator(StrategicArbitrator):
    """
    Selects the intent with the highest risk_level (assuming higher risk = higher importance/urgency)
    or other priority metric.
    """

    def select(self, candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent]]) -> Optional[
        Tuple[StrategicContextRuntime, ExecutionIntent]]:
        if not candidates:
            return None

        # Sort by risk_level descending as a proxy for priority
        # In real system, use explicit priority field
        sorted_candidates = sorted(candidates, key=lambda x: x[1].risk_level, reverse=True)

        return sorted_candidates[0]