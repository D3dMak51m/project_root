from typing import List
from src.cognitive.interfaces.narrative_generator import NarrativeGenerator
from src.cognitive.domain.semantic_interpretation import SemanticInterpretation
from src.cognitive.domain.reasoning_bundle import ReasoningBundle
from src.cognitive.domain.narrative_report import NarrativeReport


class MockNarrativeGenerator(NarrativeGenerator):
    """
    Mock implementation of NarrativeGenerator.
    Constructs deterministic text based on input structures.
    """

    def generate(
            self,
            interpretation: SemanticInterpretation,
            reasoning: ReasoningBundle
    ) -> NarrativeReport:

        # 1. Summary
        # Combine facts and sentiment into a neutral overview
        fact_count = len(interpretation.facts)
        sentiment_str = interpretation.sentiment.name.lower()
        summary = f"Analysis of {fact_count} facts indicates a {sentiment_str} context."

        # 2. Hypothesis Explanation
        # Describe the primary hypothesis without endorsing it
        if reasoning.hypotheses:
            primary_hyp = reasoning.hypotheses[0]
            hyp_expl = f"The data suggests a hypothesis: {primary_hyp.description} (Confidence: {primary_hyp.confidence:.2f})."
        else:
            hyp_expl = "No clear hypothesis formed."

        # 3. Scenario Descriptions
        # List scenarios neutrally
        scenarios = []
        for s in reasoning.scenarios:
            scenarios.append(f"Scenario: {s.description} Implications include: {', '.join(s.implications)}.")

        # 4. Risk Assessment
        # List identified risks
        if reasoning.risks:
            risk_str = f"Identified risks include: {', '.join(reasoning.risks)}."
        else:
            risk_str = "No specific risks identified."

        # 5. Uncertainty Statement
        # Highlight what is unknown
        if reasoning.uncertainties:
            unc_str = f"Analysis is limited by uncertainties: {', '.join(reasoning.uncertainties)}."
        else:
            unc_str = "No major uncertainties noted."

        return NarrativeReport(
            summary=summary,
            hypothesis_explanation=hyp_expl,
            scenario_descriptions=scenarios,
            risk_assessment=risk_str,
            uncertainty_statement=unc_str
        )