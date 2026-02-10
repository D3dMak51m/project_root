from typing import Optional
from src.autonomy.interfaces.override_resolver import OverrideResolver
from src.autonomy.domain.escalation_decision import EscalationDecision
from src.autonomy.domain.human_override_decision import HumanOverrideDecision
from src.autonomy.domain.final_execution_decision import FinalExecutionDecision


class StandardOverrideResolver(OverrideResolver):
    """
    Deterministic resolver for human overrides.
    Maps escalation status and human decisions to a final execution outcome.
    """

    def resolve(
            self,
            escalation: EscalationDecision,
            human_decision: Optional[HumanOverrideDecision]
    ) -> Optional[FinalExecutionDecision]:

        # 1. Drop Path
        if escalation == EscalationDecision.DROP:
            return FinalExecutionDecision.DROP

        # 2. Execute Path
        if escalation == EscalationDecision.EXECUTE:
            return FinalExecutionDecision.EXECUTE

        # 3. Escalation Path
        if escalation == EscalationDecision.ESCALATE_TO_HUMAN:
            if human_decision is None:
                return None  # Pending decision

            if human_decision == HumanOverrideDecision.APPROVE:
                return FinalExecutionDecision.EXECUTE

            if human_decision == HumanOverrideDecision.REJECT:
                return FinalExecutionDecision.DROP

        # Should be unreachable given enum exhaustiveness, but safe fallback
        return None