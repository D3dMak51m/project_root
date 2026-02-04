from abc import ABC, abstractmethod
from src.interaction.domain.intent import InteractionIntent
from src.interaction.domain.envelope import InteractionEnvelope

class InteractionRouter(ABC):
    """
    Interface for routing interaction intents.
    Determines WHERE and HOW an intent should be directed, but does NOT send it.
    """
    @abstractmethod
    def route(self, intent: InteractionIntent) -> InteractionEnvelope:
        pass