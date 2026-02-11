from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class RawTelegramUpdate:
    """
    Raw update data from Telegram Webhook.
    """
    update_id: int
    payload: Dict[str, Any]
    secret_token: Optional[str] = None