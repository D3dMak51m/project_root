from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class NarrativeReport:
    """
    Human-readable explanation of the system's understanding and reasoning.
    Purely descriptive, no advice or decisions.
    """
    summary: str
    hypothesis_explanation: str
    scenario_descriptions: List[str]
    risk_assessment: str
    uncertainty_statement: str