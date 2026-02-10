import pytest
from dataclasses import asdict
from typing import List
from src.cognitive.domain.semantic_interpretation import (
    SemanticInterpretation, Actor, Topic, ActorType, Sentiment, TimeHorizon
)
from src.cognitive.services.semantic_interpreter import MockSemanticInterpreter
from src.cognitive.domain.exceptions import SemanticInvariantViolation


# Fixture for the interpreter instance
@pytest.fixture
def interpreter():
    return MockSemanticInterpreter()


# Helper function for invariant enforcement
def assert_no_strategic_language(strings: List[str]):
    """
    Validates that a list of strings does not contain forbidden strategic language.
    Raises SemanticInvariantViolation if a violation is found.
    """
    forbidden_words = ["should", "must", "recommend", "best", "optimal", "ought", "need to"]

    for s in strings:
        for word in forbidden_words:
            # Simple check, in production regex might be better for word boundaries
            if word in s.lower().split():
                raise SemanticInvariantViolation(f"Forbidden strategic word '{word}' found in: '{s}'")


# 1. Determinism Tests
def test_determinism_simple_input(interpreter):
    text = "The company reported good earnings this year."
    result1 = interpreter.interpret(text)
    result2 = interpreter.interpret(text)
    assert result1 == result2


def test_determinism_complex_input(interpreter):
    text = "Despite the bad weather, the organization managed to succeed."
    result1 = interpreter.interpret(text)
    result2 = interpreter.interpret(text)
    assert asdict(result1) == asdict(result2)


# 2. Schema Validity Tests
def test_schema_salience_range(interpreter):
    text = "General topic discussion."
    result = interpreter.interpret(text)
    for topic in result.topics:
        assert 0.0 <= topic.salience <= 1.0


def test_schema_enums_validity(interpreter):
    text = "Test input."
    result = interpreter.interpret(text)
    assert isinstance(result.sentiment, Sentiment)
    assert isinstance(result.time_horizon, TimeHorizon)
    for actor in result.actors:
        assert isinstance(actor.type, ActorType)


def test_schema_completeness(interpreter):
    text = "Test input."
    result = interpreter.interpret(text)
    assert result.facts is not None
    assert result.actors is not None
    assert result.topics is not None
    assert result.uncertainties is not None


# 3. Safety Tests (No Advice) - ENHANCED
def test_no_strategic_verbs_comprehensive(interpreter):
    # Mock interpreter logic is simple, but this tests the contract on the output strings
    # We manually construct a violating result to test the assertion logic if the mock is safe

    # Test 1: Safe input
    text = "The situation is complex."
    result = interpreter.interpret(text)

    all_strings = []
    all_strings.extend(result.facts)
    all_strings.extend(result.uncertainties)
    all_strings.extend([a.name for a in result.actors])
    all_strings.extend([a.role for a in result.actors])
    all_strings.extend([t.topic for t in result.topics])

    try:
        assert_no_strategic_language(all_strings)
    except SemanticInvariantViolation:
        pytest.fail("Safe input raised SemanticInvariantViolation")

    # Test 2: Unsafe input simulation (Manual check of helper)
    unsafe_strings = [
        "Government should intervene",  # Fact
        "We must act now",  # Uncertainty
        "Best Actor",  # Name
        "Optimal Strategy Group",  # Role
        "Recommended Policy"  # Topic
    ]

    for s in unsafe_strings:
        with pytest.raises(SemanticInvariantViolation):
            assert_no_strategic_language([s])


# 4. Data Purity Tests
def test_data_purity(interpreter):
    text = "Pure data check."
    result = interpreter.interpret(text)

    # Ensure everything is serializable / pure data
    try:
        data_dict = asdict(result)
        # Basic check for callables
        for key, value in data_dict.items():
            assert not callable(value), f"Field {key} is callable"
    except Exception as e:
        pytest.fail(f"Result is not pure data: {e}")