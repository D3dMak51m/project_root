from abc import ABC, abstractmethod
from src.autonomy.domain.final_execution_decision import FinalExecutionDecision
from src.core.config.runtime_profile import RuntimeProfile
from src.core.domain.runtime_phase import RuntimePhase
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision

class ExecutionGate(ABC):
    """
    Interface for the final execution gate.
    Ensures no action is taken if the environment or profile forbids it.
    Must be pure and deterministic.
    """
    @abstractmethod
    def evaluate(
        self,
        final_decision: FinalExecutionDecision,
        profile: RuntimeProfile,
        runtime_phase: RuntimePhase
    ) -> ExecutionGateDecision:
        pass