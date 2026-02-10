from dataclasses import dataclass
from typing import Optional

class TelegramError(Exception):
    """Base class for Telegram API errors."""
    pass

@dataclass
class TelegramApiError(TelegramError):
    """Error returned by Telegram API."""
    error_code: int
    description: str
    parameters: Optional[dict] = None

class TelegramNetworkError(TelegramError):
    """Network connectivity error."""
    pass

class TelegramRateLimitError(TelegramApiError):
    """HTTP 429 or specific rate limit error code."""
    retry_after: int = 0

class TelegramForbiddenError(TelegramApiError):
    """Bot blocked or kicked."""
    pass