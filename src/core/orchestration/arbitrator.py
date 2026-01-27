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
    def select(
            self,
            candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent, float]]  # Added priority_score
    ) -> Optional[Tuple[StrategicContextRuntime, ExecutionIntent]]:
        pass


class PriorityArbitrator(StrategicArbitrator):
    """
    Selects the intent with the highest calculated priority score.
    """

    def select(
            self,
            candidates: List[Tuple[StrategicContextRuntime, ExecutionIntent, float]]
    ) -> Optional[Tuple[StrategicContextRuntime, ExecutionIntent]]:
        if not candidates:
            return None

        # Sort by priority_score descending
        # candidates is list of (runtime, intent, priority_score)
        sorted_candidates = sorted(candidates, key=lambda x: x[2], reverse=True)

        winner = sorted_candidates[0]
        return winner[0], winner[1]