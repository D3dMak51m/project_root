from abc import ABC, abstractmethod
from src.core.context.internal import InternalContext
from src.core.domain.thought import ThoughtArtifact

class ThinkingEngine(ABC):
    """
    Pure cognitive reflection.
    No state mutation allowed.
    """

    @abstractmethod
    def think(self, context: InternalContext) -> ThoughtArtifact:
        pass