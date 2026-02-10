from abc import ABC, abstractmethod
from typing import Optional
from src.autonomy.domain.escalation_decision import EscalationDecision
from src.autonomy.domain.human_override_decision import HumanOverrideDecision
from src.autonomy.domain.final_execution_decision import FinalExecutionDecision

class OverrideResolver(ABC):
    """
    Interface for resolving the final execution decision based on escalation status and human input.
    Must be pure and deterministic.
    """
    @abstractmethod
    def resolve(
        self,
        escalation: EscalationDecision,
        human_decision: Optional[HumanOverrideDecision]
    ) -> Optional[FinalExecutionDecision]:
        pass