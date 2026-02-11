from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from src.infrastructure.inbound.telegram.telegram_update_dto import RawTelegramUpdate
from src.interaction.domain.interaction_event import InteractionEvent


class TelegramUpdateNormalizer:
    """
    Pure service. Normalizes raw Telegram updates into canonical InteractionEvents.
    """

    def normalize(self, update: RawTelegramUpdate) -> Optional[InteractionEvent]:
        payload = update.payload

        # We only handle 'message' updates for now
        message = payload.get("message")
        if not message:
            return None

        user = message.get("from", {})
        chat = message.get("chat", {})
        text = message.get("text", "")

        # Determine message type
        msg_type = "text"
        if text.startswith("/"):
            msg_type = "command"

        # Timestamp from message date (unix timestamp)
        ts = datetime.fromtimestamp(message.get("date", 0), tz=timezone.utc)

        return InteractionEvent(
            id=uuid4(),
            platform="telegram",
            user_id=str(user.get("id")),
            chat_id=str(chat.get("id")),
            content=text,
            message_type=msg_type,
            timestamp=ts,
            raw_metadata={"update_id": update.update_id}
        )