from abc import ABC, abstractmethod
from src.autonomy.domain.silence_decision import SilenceDecision
from src.autonomy.domain.autonomy_state import AutonomyState
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile
from src.autonomy.domain.escalation_decision import EscalationDecision

class EscalationEvaluator(ABC):
    """
    Interface for evaluating whether to execute, escalate, or drop an action.
    Must be pure and deterministic.
    """
    @abstractmethod
    def evaluate(
        self,
        silence: SilenceDecision,
        autonomy: AutonomyState,
        policy: PolicyDecision,
        profile: RuntimeProfile
    ) -> EscalationDecision:
        pass