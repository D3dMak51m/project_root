import json
from typing import Any, Dict
from src.cognitive.interfaces.semantic_interpreter import SemanticInterpreter
from src.cognitive.domain.semantic_interpretation import (
    SemanticInterpretation, Actor, Topic, ActorType, Sentiment, TimeHorizon
)


# In a real implementation, this would wrap an LLM call.
# For this stage, we implement a mock/stub or a simple rule-based parser
# to demonstrate the architectural contract.
# Since the prompt implies I am the module, I will provide a mock implementation
# that simulates the behavior described in the prompt for testing purposes.

class MockSemanticInterpreter(SemanticInterpreter):
    """
    Mock implementation of SemanticInterpreter for testing/validation.
    Returns deterministic structure based on keywords or predefined mappings.
    """

    def interpret(self, text: str) -> SemanticInterpretation:
        # Simple keyword-based mock logic

        # Sentiment
        sentiment = Sentiment.NEUTRAL
        if "good" in text or "success" in text:
            sentiment = Sentiment.POSITIVE
        elif "bad" in text or "fail" in text:
            sentiment = Sentiment.NEGATIVE

        # Time Horizon
        horizon = TimeHorizon.SHORT
        if "year" in text or "decade" in text:
            horizon = TimeHorizon.LONG
        elif "month" in text:
            horizon = TimeHorizon.MID

        # Facts (Mock extraction)
        facts = [f"Input contains {len(text)} characters"]

        # Actors (Mock)
        actors = []
        if "Company" in text:
            actors.append(Actor("Company", ActorType.ORGANIZATION, "Mentioned entity"))

        # Topics
        topics = [Topic("general", 0.5)]

        return SemanticInterpretation(
            facts=facts,
            actors=actors,
            topics=topics,
            sentiment=sentiment,
            uncertainties=["Context is missing"],
            time_horizon=horizon
        )


class LLMSemanticInterpreter(SemanticInterpreter):
    """
    Placeholder for real LLM-based implementation.
    This class would construct the prompt defined in H.1 and parse the JSON response.
    """

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def interpret(self, text: str) -> SemanticInterpretation:
        # 1. Construct Prompt (using the H.1 prompt template)
        # 2. Call LLM
        # 3. Parse JSON
        # 4. Map to Domain Objects
        # This is a stub for the architectural layer.
        raise NotImplementedError("LLM integration not yet implemented")