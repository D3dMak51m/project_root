from typing import List
from src.world.store.world_observation_store import WorldObservationStore
from src.world.domain.world_observation import WorldObservation


class ConversationMemoryAdapter:
    """
    Service to retrieve relevant observations for a specific dialogue context.
    Filters the global WorldObservationStore.
    """

    def __init__(self, store: WorldObservationStore):
        self.store = store

    def get_recent_context(self, context_domain: str, limit: int = 10) -> List[WorldObservation]:
        """
        Returns the last N observations relevant to the given context_domain.
        """
        all_obs = self.store.list_all()

        # Filter by context domain first. Fallback to deterministic telegram domain mapping
        # for observations produced before context_domain was added.
        relevant_obs = [
            obs for obs in all_obs
            if (
                obs.context_domain == context_domain
                or (
                    not obs.context_domain
                    and obs.interaction
                    and f"telegram:{obs.interaction.chat_id}" == context_domain
                )
            )
        ]

        # Sort by timestamp descending (newest first) then take limit
        # Note: list_all usually returns append-order (oldest first).
        # We want recent context, so we take from the end.
        return relevant_obs[-limit:]