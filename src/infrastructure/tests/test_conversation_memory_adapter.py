from datetime import datetime, timezone
from uuid import uuid4

from src.infrastructure.services.conversation_memory_adapter import ConversationMemoryAdapter
from src.interaction.domain.interaction_event import InteractionEvent
from src.world.domain.world_observation import WorldObservation
from src.world.store.world_observation_store import WorldObservationStore


def _interaction(chat_id: str, user_id: str):
    return InteractionEvent(
        id=uuid4(),
        platform="telegram",
        user_id=user_id,
        chat_id=chat_id,
        content="msg",
        message_type="text",
        timestamp=datetime.now(timezone.utc),
        raw_metadata={}
    )


def test_conversation_memory_filters_by_context_domain():
    store = WorldObservationStore()
    adapter = ConversationMemoryAdapter(store)

    # Same chat id but different domains to simulate future multi-tenant routing.
    obs_a = WorldObservation(interaction=_interaction("100", "u1"), context_domain="telegram:100")
    obs_b = WorldObservation(interaction=_interaction("100", "u2"), context_domain="tenantX:telegram:100")
    obs_legacy = WorldObservation(interaction=_interaction("100", "u3"), context_domain=None)

    store.append(obs_a)
    store.append(obs_b)
    store.append(obs_legacy)

    scoped = adapter.get_recent_context("telegram:100", limit=10)

    assert obs_a in scoped
    assert obs_b not in scoped
    # Legacy observations without explicit context_domain still map deterministically.
    assert obs_legacy in scoped
