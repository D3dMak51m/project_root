from abc import ABC, abstractmethod
from src.cognitive.domain.semantic_interpretation import SemanticInterpretation
from src.cognitive.domain.reasoning_bundle import ReasoningBundle
from src.cognitive.domain.narrative_report import NarrativeReport


class NarrativeGenerator(ABC):
    """
    Interface for generating human-readable narratives from structured analysis.
    Must be pure, stateless, and authority-free.
    """

    @abstractmethod
    def generate(
            self,
            interpretation: SemanticInterpretation,
            reasoning: ReasoningBundle
    ) -> NarrativeReport:
        """
        Convert interpretation and reasoning into a narrative report.
        """
        pass