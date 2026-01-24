from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.core.domain.strategic_signals import StrategicSignals


class StrategicFeedbackInterpreter:
    """
    Pure service.
    Translates execution feedback into strategic meaning.
    Does NOT touch state, intentions, or readiness.
    Operates ONLY on the result fact.
    """

    def interpret(
            self,
            result: ExecutionResult
    ) -> StrategicSignals:

        if result.status == ExecutionStatus.SUCCESS:
            return StrategicSignals(
                outcome_classification="success",
                confidence_delta=0.2,
                risk_reassessment=0.1,
                persistence_bias=0.5,
                notes=["Action successful, strategy validated"]
            )

        elif result.status == ExecutionStatus.FAILED:
            if result.failure_type == ExecutionFailureType.ENVIRONMENT:
                return StrategicSignals(
                    outcome_classification="hostile_env",
                    confidence_delta=-0.1,
                    risk_reassessment=0.3,
                    persistence_bias=1.5,
                    notes=["Environment failure, persistence required"]
                )
            elif result.failure_type == ExecutionFailureType.INTERNAL:
                return StrategicSignals(
                    outcome_classification="unstable",
                    confidence_delta=-0.05,
                    risk_reassessment=0.0,
                    persistence_bias=1.0,
                    notes=["Internal error, no strategic conclusion"]
                )

        elif result.status == ExecutionStatus.REJECTED:
            if result.failure_type == ExecutionFailureType.POLICY:
                return StrategicSignals(
                    outcome_classification="blocked",
                    confidence_delta=-0.2,
                    risk_reassessment=-0.4,
                    persistence_bias=0.3,
                    notes=["Policy rejection, strategy adjustment needed"]
                )

        elif result.status == ExecutionStatus.PARTIAL:
            return StrategicSignals(
                outcome_classification="partial",
                confidence_delta=0.05,
                risk_reassessment=0.2,
                persistence_bias=1.2,
                notes=["Partial success, requires follow-up"]
            )

        # Default fallback
        return StrategicSignals(
            outcome_classification="unknown",
            confidence_delta=0.0,
            risk_reassessment=0.0,
            persistence_bias=1.0,
            notes=["Unknown outcome"]
        )