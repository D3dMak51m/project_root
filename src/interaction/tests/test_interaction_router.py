import pytest
from uuid import uuid4
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.interaction.domain.envelope import InteractionEnvelope, TargetHint, PriorityHint, Visibility
from src.interaction.services.router import StandardInteractionRouter


def create_intent(type: InteractionType, target_id: str = None) -> InteractionIntent:
    return InteractionIntent(
        id=uuid4(),
        type=type,
        content="test content",
        metadata={},
        target_id=target_id
    )


def test_router_determinism():
    router = StandardInteractionRouter()
    intent = create_intent(InteractionType.REPORT)

    env1 = router.route(intent)
    env2 = router.route(intent)

    assert env1 == env2


def test_report_routing():
    router = StandardInteractionRouter()
    intent = create_intent(InteractionType.REPORT)
    envelope = router.route(intent)

    assert envelope.target_hint == TargetHint.ADMIN
    assert envelope.visibility == Visibility.INTERNAL
    assert envelope.priority_hint == PriorityHint.LOW


def test_message_routing():
    router = StandardInteractionRouter()
    intent = create_intent(InteractionType.MESSAGE, target_id="user_123")
    envelope = router.route(intent)

    assert envelope.target_hint == TargetHint.USER
    assert envelope.visibility == Visibility.EXTERNAL
    assert envelope.routing_key == "user_123"


def test_confirmation_routing():
    router = StandardInteractionRouter()
    intent = create_intent(InteractionType.CONFIRMATION_REQUEST)
    envelope = router.route(intent)

    assert envelope.priority_hint == PriorityHint.HIGH
    assert envelope.target_hint == TargetHint.ADMIN