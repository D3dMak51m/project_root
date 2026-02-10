import pytest
from dataclasses import asdict
from src.cognitive.domain.semantic_interpretation import (
    SemanticInterpretation, Actor, Topic, ActorType, Sentiment, TimeHorizon
)
from src.cognitive.domain.reasoning_bundle import (
    ReasoningBundle, Hypothesis, CausalLink, Constraint, Scenario
)
from src.cognitive.domain.narrative_report import NarrativeReport
from src.cognitive.services.narrative_generator import MockNarrativeGenerator
from src.cognitive.domain.exceptions import SemanticInvariantViolation


@pytest.fixture
def generator():
    return MockNarrativeGenerator()


@pytest.fixture
def sample_data():
    interp = SemanticInterpretation(
        facts=["Event A occurred."],
        actors=[],
        topics=[],
        sentiment=Sentiment.NEUTRAL,
        uncertainties=["Cause unknown"],
        time_horizon=TimeHorizon.SHORT
    )
    reasoning = ReasoningBundle(
        hypotheses=[Hypothesis("Event A is isolated.", [], 0.8)],
        causal_links=[],
        constraints=[],
        scenarios=[Scenario("Nothing changes.", ["Stability"], "high")],
        risks=["Data lag"],
        uncertainties=["Cause unknown"]
    )
    return interp, reasoning


def assert_no_strategic_language(strings: list[str]):
    forbidden_words = ["should", "must", "recommend", "best", "optimal", "ought", "need to"]
    for s in strings:
        for word in forbidden_words:
            if word in s.lower().split():
                raise SemanticInvariantViolation(f"Forbidden strategic word '{word}' found in: '{s}'")


def test_narrative_structure(generator, sample_data):
    interp, reasoning = sample_data
    report = generator.generate(interp, reasoning)

    assert isinstance(report, NarrativeReport)
    assert report.summary
    assert report.hypothesis_explanation
    assert len(report.scenario_descriptions) > 0
    assert report.risk_assessment
    assert report.uncertainty_statement


def test_narrative_purity(generator, sample_data):
    interp, reasoning = sample_data
    report = generator.generate(interp, reasoning)

    all_strings = [
        report.summary,
        report.hypothesis_explanation,
        report.risk_assessment,
        report.uncertainty_statement
    ]
    all_strings.extend(report.scenario_descriptions)

    assert_no_strategic_language(all_strings)


def test_determinism(generator, sample_data):
    interp, reasoning = sample_data
    report1 = generator.generate(interp, reasoning)
    report2 = generator.generate(interp, reasoning)
    assert asdict(report1) == asdict(report2)