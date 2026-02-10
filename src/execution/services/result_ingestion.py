from dataclasses import replace
from src.execution.interfaces.result_ingestion import ResultIngestionService
from src.core.domain.execution_result import ExecutionResult
from src.core.lifecycle.signals import LifeSignals

class StandardResultIngestionService(ResultIngestionService):
    """
    Deterministic ingestion service.
    Attaches execution feedback to LifeSignals without side effects.
    """
    def ingest(
        self,
        result: ExecutionResult,
        signals: LifeSignals
    ) -> LifeSignals:
        # Return a new LifeSignals object with the feedback attached
        # Using replace to ensure immutability of the original object if it were frozen
        # (LifeSignals is a dataclass, so replace works)
        return replace(signals, execution_feedback=result)