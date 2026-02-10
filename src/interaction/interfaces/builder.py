from abc import ABC, abstractmethod
from typing import List
from src.interaction.domain.context import InteractionContext
from src.interaction.domain.intent import InteractionIntent

class InteractionBuilder(ABC):
    """
    Interface for building interaction intents from context.
    Must be pure and deterministic.
    """
    @abstractmethod
    def build(self, context: InteractionContext) -> List[InteractionIntent]:
        pass