from dataclasses import dataclass
from typing import List
from src.world.domain.world_observation import WorldObservation
from src.cognitive.domain.semantic_interpretation import SemanticInterpretation
from src.cognitive.domain.reasoning_bundle import ReasoningBundle
from src.cognitive.domain.narrative_report import NarrativeReport

@dataclass(frozen=True)
class InteractionContext:
    """
    Aggregated context required to form an interaction.
    Combines world observations with cognitive analysis.
    Pure data, no decisions.
    """
    observations: List[WorldObservation]
    interpretation: SemanticInterpretation
    reasoning: ReasoningBundle
    narrative: NarrativeReport