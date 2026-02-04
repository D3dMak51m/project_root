from abc import ABC, abstractmethod
from src.cognitive.domain.semantic_interpretation import SemanticInterpretation
from src.cognitive.domain.reasoning_bundle import ReasoningBundle


class StrategicReasoner(ABC):
    """
    Interface for the Strategic Reasoning Engine.
    Transforms semantic interpretation into structured reasoning.
    Must be pure, stateless, and authority-free.
    """

    @abstractmethod
    def reason(self, interpretation: SemanticInterpretation) -> ReasoningBundle:
        """
        Analyze the semantic interpretation and produce a reasoning bundle.
        """
        pass