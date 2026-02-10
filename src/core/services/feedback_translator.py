from datetime import datetime
from typing import List

from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.core.domain.execution_intent import ExecutionIntent
from src.core.lifecycle.signals import LifeSignals


class ExecutionFeedbackTranslator:
    """
    Pure service. Translates raw ExecutionResult into LifeSignals.
    Strictly factual: maps costs and status codes to signals without interpretation.
    Does NOT assign meaning (success/failure emotion), only reports facts.
    """

    def translate(
            self,
            result: ExecutionResult,
            intent: ExecutionIntent,
            now: datetime
    ) -> LifeSignals:

        energy_delta = 0.0
        memories: List[str] = []

        # 1. Map Status to Diagnostic Memory (Fact-based)
        if result.status == ExecutionStatus.SUCCESS:
            memories.append(f"execution_status=SUCCESS action={intent.abstract_action}")

        elif result.status == ExecutionStatus.REJECTED:
            memories.append(f"execution_status=REJECTED type={result.failure_type.name} reason={result.reason}")

        elif result.status == ExecutionStatus.FAILED:
            memories.append(f"execution_status=FAILED type={result.failure_type.name} reason={result.reason}")

        elif result.status == ExecutionStatus.PARTIAL:
            memories.append(f"execution_status=PARTIAL reason={result.reason}")

        # 2. Map Costs (Fact-based)
        # Only reflect actual energy consumed by the attempt.
        # Does not interpret "wasted" vs "useful" energy.
        if "energy" in result.costs:
            # Energy cost is always negative (consumption)
            energy_delta = -abs(result.costs["energy"])

        # Fallback for internal failures where cost might not be reported but exists
        if result.status == ExecutionStatus.FAILED and energy_delta == 0.0:
            energy_delta = -1.0  # Minimal cost for processing failure

        # 3. Construct Neutral Signals
        # Pressure delta is ALWAYS 0.0 here. Interpretation happens in LifeLoop/Strategy.
        return LifeSignals(
            pressure_delta=0.0,
            energy_delta=energy_delta,
            attention_delta=0.0,
            rest=False,
            perceived_topics={},
            memories=memories,
            execution_feedback=result
        )