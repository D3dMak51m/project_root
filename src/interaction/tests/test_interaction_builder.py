import pytest
from uuid import uuid4
from datetime import datetime, timezone
from src.interaction.domain.context import InteractionContext
from src.interaction.domain.intent import InteractionType
from src.interaction.services.builder import StandardInteractionBuilder
from src.world.domain.world_observation import WorldObservation
from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import SignalSalience
from src.world.domain.target import TargetBinding
from src.cognitive.domain.semantic_interpretation import SemanticInterpretation, Sentiment, TimeHorizon
from src.cognitive.domain.reasoning_bundle import ReasoningBundle
from src.cognitive.domain.narrative_report import NarrativeReport


# --- Helpers ---

def create_dummy_context(salience_score=0.5, uncertainties=None):
    if uncertainties is None:
        uncertainties = []

    signal = NormalizedSignal(uuid4(), "src", datetime.now(timezone.utc), datetime.now(timezone.utc), "content", {})
    salience = SignalSalience(signal.signal_id, "src", signal.received_at, 0.5, 0.5, 0.5, salience_score)
    obs = WorldObservation(signal, salience, [], TargetBinding(signal.signal_id))

    interp = SemanticInterpretation([], [], [], Sentiment.NEUTRAL, [], TimeHorizon.SHORT)
    reasoning = ReasoningBundle([], [], [], [], [], uncertainties)
    narrative = NarrativeReport("Summary", "Hypothesis", [], "Risk", "Uncertainty")

    return InteractionContext([obs], interp, reasoning, narrative)


# --- Tests ---

def test_builder_determinism():
    builder = StandardInteractionBuilder()
    context = create_dummy_context()

    intents1 = builder.build(context)
    intents2 = builder.build(context)

    assert len(intents1) == len(intents2)
    assert intents1[0].content == intents2[0].content
    assert intents1[0].type == intents2[0].type


def test_report_generation():
    builder = StandardInteractionBuilder()
    context = create_dummy_context()
    intents = builder.build(context)

    report_intents = [i for i in intents if i.type == InteractionType.REPORT]
    assert len(report_intents) == 1
    assert report_intents[0].content == "Summary"


def test_question_generation():
    builder = StandardInteractionBuilder()
    context = create_dummy_context(uncertainties=["Unknown X", "Missing Y"])
    intents = builder.build(context)

    question_intents = [i for i in intents if i.type == InteractionType.QUESTION]
    assert len(question_intents) == 1
    assert "Unknown X" in question_intents[0].content


def test_notification_generation():
    builder = StandardInteractionBuilder()
    # High salience to trigger notification
    context = create_dummy_context(salience_score=0.9)
    intents = builder.build(context)

    notif_intents = [i for i in intents if i.type == InteractionType.NOTIFICATION]
    assert len(notif_intents) == 1
    assert "High salience" in notif_intents[0].content


def test_no_strategic_language():
    builder = StandardInteractionBuilder()
    context = create_dummy_context()
    intents = builder.build(context)

    forbidden = ["should", "must", "recommend", "best"]
    for intent in intents:
        for word in forbidden:
            assert word not in intent.content.lower()