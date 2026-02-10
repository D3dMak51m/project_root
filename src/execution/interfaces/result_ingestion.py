from abc import ABC, abstractmethod
from src.core.domain.execution_result import ExecutionResult
from src.core.lifecycle.signals import LifeSignals

class ResultIngestionService(ABC):
    """
    Interface for ingesting execution results back into the system lifecycle.
    Must be pure and return a new LifeSignals object.
    """
    @abstractmethod
    def ingest(
        self,
        result: ExecutionResult,
        signals: LifeSignals
    ) -> LifeSignals:
        pass