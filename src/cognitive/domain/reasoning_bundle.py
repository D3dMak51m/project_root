from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass(frozen=True)
class Hypothesis:
    description: str
    supporting_facts: List[str]
    confidence: float # 0.0 - 1.0, analytical confidence, not preference

@dataclass(frozen=True)
class CausalLink:
    source: str # Actor/Topic/Fact
    target: str # Actor/Topic/Fact
    relationship: str # e.g., "influences", "opposes", "causes"

@dataclass(frozen=True)
class Constraint:
    type: str # "political", "economic", "temporal", "informational"
    description: str

@dataclass(frozen=True)
class Scenario:
    description: str
    implications: List[str]
    likelihood_assessment: str # "low", "medium", "high", "unknown" - descriptive only

@dataclass(frozen=True)
class ReasoningBundle:
    """
    Pure analytical artifact produced by the Strategic Reasoning Engine.
    Contains structured analysis without decisions or recommendations.
    """
    hypotheses: List[Hypothesis]
    causal_links: List[CausalLink]
    constraints: List[Constraint]
    scenarios: List[Scenario]
    risks: List[str]
    uncertainties: List[str]