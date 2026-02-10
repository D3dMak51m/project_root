from typing import List
from src.cognitive.interfaces.strategic_reasoner import StrategicReasoner
from src.cognitive.domain.semantic_interpretation import SemanticInterpretation
from src.cognitive.domain.reasoning_bundle import (
    ReasoningBundle, Hypothesis, CausalLink, Constraint, Scenario
)


class MockStrategicReasoner(StrategicReasoner):
    """
    Mock implementation of StrategicReasoner for testing/validation.
    Simulates analytical output based on input interpretation.
    """

    def reason(self, interpretation: SemanticInterpretation) -> ReasoningBundle:
        # 1. Generate Hypotheses
        hypotheses = []
        if interpretation.sentiment.name == "NEGATIVE":
            hypotheses.append(Hypothesis(
                description="Negative sentiment may indicate underlying conflict.",
                supporting_facts=interpretation.facts[:2],
                confidence=0.7
            ))
        else:
            hypotheses.append(Hypothesis(
                description="Situation appears stable.",
                supporting_facts=interpretation.facts[:1],
                confidence=0.5
            ))

        # 2. Identify Causal Links
        links = []
        if interpretation.actors and interpretation.topics:
            links.append(CausalLink(
                source=interpretation.actors[0].name,
                target=interpretation.topics[0].topic,
                relationship="associated_with"
            ))

        # 3. Identify Constraints
        constraints = []
        if interpretation.time_horizon.name == "SHORT":
            constraints.append(Constraint("temporal", "Short time horizon limits long-term planning."))

        # 4. Enumerate Scenarios
        scenarios = [
            Scenario(
                description="Status quo continues.",
                implications=["No major changes."],
                likelihood_assessment="medium"
            ),
            Scenario(
                description="Rapid escalation.",
                implications=["Increased volatility."],
                likelihood_assessment="low"
            )
        ]

        # 5. Map Risks and Uncertainties
        risks = ["Misinterpretation of signals", "Data incompleteness"]
        uncertainties = list(interpretation.uncertainties)

        return ReasoningBundle(
            hypotheses=hypotheses,
            causal_links=links,
            constraints=constraints,
            scenarios=scenarios,
            risks=risks,
            uncertainties=uncertainties
        )