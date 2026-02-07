from src.autonomy.interfaces.escalation_evaluator import EscalationEvaluator
from src.autonomy.domain.escalation_decision import EscalationDecision
from src.autonomy.domain.silence_decision import SilenceDecision
from src.autonomy.domain.autonomy_state import AutonomyState
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile


class StandardEscalationEvaluator(EscalationEvaluator):
    """
    Deterministic evaluator for escalation logic.
    Enforces human oversight based on autonomy state and policy constraints.
    """

    def evaluate(
            self,
            silence: SilenceDecision,
            autonomy: AutonomyState,
            policy: PolicyDecision,
            profile: RuntimeProfile
    ) -> EscalationDecision:

        # 1. Silence Check
        if silence == SilenceDecision.SILENCE:
            return EscalationDecision.DROP

        # 2. Autonomy Requirement Check
        if autonomy.requires_human:
            return EscalationDecision.ESCALATE_TO_HUMAN

        # 3. Policy Constraints Check
        escalation_triggers = {"requires_approval", "audit_logging", "high_risk"}
        if any(c in escalation_triggers for c in policy.constraints):
            return EscalationDecision.ESCALATE_TO_HUMAN

        # 4. Default Execute
        return EscalationDecision.EXECUTE