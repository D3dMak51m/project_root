from abc import ABC, abstractmethod
from src.interaction.domain.envelope import InteractionEnvelope
from src.interaction.domain.policy_decision import PolicyDecision
from src.core.config.runtime_profile import RuntimeProfile
from src.autonomy.domain.autonomy_state import AutonomyState

class AutonomyStateEvaluator(ABC):
    """
    Interface for evaluating autonomy readiness.
    Must be pure and deterministic.
    """
    @abstractmethod
    def evaluate(
        self,
        envelope: InteractionEnvelope,
        policy: PolicyDecision,
        profile: RuntimeProfile
    ) -> AutonomyState:
        pass