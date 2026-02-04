from abc import ABC, abstractmethod
from src.cognitive.domain.semantic_interpretation import SemanticInterpretation


class SemanticInterpreter(ABC):
    """
    Interface for converting unstructured text into structured semantic data.
    Must be pure, stateless, and authority-free.
    """

    @abstractmethod
    def interpret(self, text: str) -> SemanticInterpretation:
        """
        Analyze the input text and return a structured interpretation.
        """
        pass