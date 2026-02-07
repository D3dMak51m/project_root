from abc import ABC, abstractmethod
from src.autonomy.domain.initiative_decision import InitiativeDecision
from src.interaction.domain.envelope import InteractionEnvelope
from src.autonomy.domain.autonomy_state import AutonomyState
from src.core.config.runtime_profile import RuntimeProfile
from src.autonomy.domain.silence_profile import SilenceProfile
from src.autonomy.domain.silence_decision import SilenceDecision

class SilenceEvaluator(ABC):
    """
    Interface for evaluating whether to maintain silence or allow action.
    Must be pure and deterministic.
    """
    @abstractmethod
    def evaluate(
        self,
        initiative: InitiativeDecision,
        envelope: InteractionEnvelope,
        autonomy: AutonomyState,
        profile: RuntimeProfile,
        silence_profile: SilenceProfile
    ) -> SilenceDecision:
        pass