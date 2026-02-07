from abc import ABC, abstractmethod
from src.interaction.domain.envelope import InteractionEnvelope
from src.interaction.domain.policy_decision import PolicyDecision
from src.autonomy.domain.autonomy_state import AutonomyState
from src.core.config.runtime_profile import RuntimeProfile
from src.autonomy.domain.initiative_decision import InitiativeDecision

class InitiativeEngine(ABC):
    """
    Interface for determining whether the system should initiate an action.
    Must be pure and deterministic.
    """
    @abstractmethod
    def evaluate(
        self,
        envelope: InteractionEnvelope,
        policy: PolicyDecision,
        autonomy: AutonomyState,
        profile: RuntimeProfile
    ) -> InitiativeDecision:
        pass