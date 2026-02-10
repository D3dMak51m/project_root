from src.autonomy.interfaces.execution_gate import ExecutionGate
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.autonomy.domain.final_execution_decision import FinalExecutionDecision
from src.core.config.runtime_profile import RuntimeProfile
from src.core.domain.runtime_phase import RuntimePhase


class StandardExecutionGate(ExecutionGate):
    """
    Deterministic execution gate.
    Enforces runtime safety and phase constraints.
    """

    def evaluate(
            self,
            final_decision: FinalExecutionDecision,
            profile: RuntimeProfile,
            runtime_phase: RuntimePhase
    ) -> ExecutionGateDecision:

        # 1. Decision Check
        if final_decision == FinalExecutionDecision.DROP:
            return ExecutionGateDecision.DENY

        # 2. Runtime Phase Check (Replay Safety)
        if runtime_phase == RuntimePhase.REPLAY:
            return ExecutionGateDecision.DENY

        # 3. Profile Execution Permission Check
        if not profile.allow_execution:
            return ExecutionGateDecision.DENY

        # 4. All Checks Passed
        return ExecutionGateDecision.ALLOW