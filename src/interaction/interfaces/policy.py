from abc import ABC, abstractmethod
from interaction.domain.policy_decision import PolicyDecision
from src.interaction.domain.envelope import InteractionEnvelope
from src.core.config.runtime_profile import RuntimeProfile

class InteractionPolicy(ABC):
    """
    Interface for evaluating interaction policies.
    Must be pure and deterministic given the envelope and profile.
    """
    @abstractmethod
    def evaluate(
        self,
        envelope: InteractionEnvelope,
        profile: RuntimeProfile
    ) -> PolicyDecision:
        pass