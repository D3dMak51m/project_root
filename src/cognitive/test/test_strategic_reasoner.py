import pytest
from dataclasses import asdict
from src.cognitive.domain.semantic_interpretation import (
    SemanticInterpretation, Actor, Topic, ActorType, Sentiment, TimeHorizon
)
from src.cognitive.domain.reasoning_bundle import ReasoningBundle
from src.cognitive.services.strategic_reasoner import MockStrategicReasoner
from src.cognitive.domain.exceptions import SemanticInvariantViolation


@pytest.fixture
def reasoner():
    return MockStrategicReasoner()


@pytest.fixture
def sample_interpretation():
    return SemanticInterpretation(
        facts=["Market is volatile.", "Competitor X launched product Y."],
        actors=[Actor("Competitor X", ActorType.ORGANIZATION, "Rival")],
        topics=[Topic("Market", 0.9)],
        sentiment=Sentiment.NEGATIVE,
        uncertainties=["Consumer reaction unknown"],
        time_horizon=TimeHorizon.SHORT
    )


def assert_no_strategic_language(strings: list[str]):
    forbidden_words = ["should", "must", "recommend", "best", "optimal", "ought", "need to"]
    for s in strings:
        for word in forbidden_words:
            if word in s.lower().split():
                raise SemanticInvariantViolation(f"Forbidden strategic word '{word}' found in: '{s}'")


def test_reasoning_structure(reasoner, sample_interpretation):
    bundle = reasoner.reason(sample_interpretation)
    assert isinstance(bundle, ReasoningBundle)
    assert len(bundle.hypotheses) > 0
    assert len(bundle.scenarios) > 0
    assert len(bundle.constraints) > 0


def test_reasoning_purity(reasoner, sample_interpretation):
    # Ensure no advice in output strings
    bundle = reasoner.reason(sample_interpretation)

    all_strings = []
    for h in bundle.hypotheses:
        all_strings.append(h.description)
    for s in bundle.scenarios:
        all_strings.append(s.description)
        all_strings.extend(s.implications)

    assert_no_strategic_language(all_strings)


def test_determinism(reasoner, sample_interpretation):
    bundle1 = reasoner.reason(sample_interpretation)
    bundle2 = reasoner.reason(sample_interpretation)
    assert asdict(bundle1) == asdict(bundle2)