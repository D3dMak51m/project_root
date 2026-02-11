from src.core.domain.strategic_context import StrategicContext


class DialogueContextResolver:
    """
    Pure service. Maps a Telegram chat_id to a StrategicContext.
    Ensures isolation between different conversations.
    """

    def resolve(self, chat_id: str) -> StrategicContext:
        # In a real system, this might look up a persistent mapping.
        # For T3, we deterministically generate a context based on chat_id.

        # Domain format: "telegram:{chat_id}"
        domain = f"telegram:{chat_id}"

        return StrategicContext(
            country="global",  # Default
            region=None,
            goal_id=None,
            domain=domain
        )