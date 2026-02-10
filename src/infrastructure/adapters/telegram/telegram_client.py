import time
import json
import logging
import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.infrastructure.adapters.telegram.telegram_errors import (
    TelegramError, TelegramApiError, TelegramNetworkError,
    TelegramRateLimitError, TelegramForbiddenError
)

logger = logging.getLogger(__name__)


class TelegramClient:
    """
    Production-grade HTTP client for Telegram Bot API.
    Handles retries, backoff, and error normalization.
    """

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str, max_retries: int = 3, timeout: int = 10):
        self.token = token
        self.timeout = timeout
        self.session = self._create_session(max_retries)

    def _create_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.0,  # 1s, 2s, 4s...
            status_forcelist=[500, 502, 503, 504],  # Removed 429 to handle manually
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def send_message(self, chat_id: str, text: str, parse_mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends a text message.
        Raises normalized TelegramError on failure.
        """
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        return self._post("sendMessage", payload)

    def _post(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = self.BASE_URL.format(token=self.token, method=method)

        try:
            response = self.session.post(url, json=data, timeout=self.timeout)

            # Handle 429 explicitly
            if response.status_code == 429:
                retry_after = int(response.json().get("parameters", {}).get("retry_after", 5))
                logger.warning(f"Telegram Rate Limit 429. Sleeping for {retry_after}s")
                time.sleep(retry_after)
                # Retry once
                response = self.session.post(url, json=data, timeout=self.timeout)

            response_data = response.json()

        except requests.RequestException as e:
            logger.error(f"Telegram network error: {e}")
            raise TelegramNetworkError(f"Request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Telegram invalid JSON: {e}")
            raise TelegramNetworkError("Invalid JSON response") from e

        if not response_data.get("ok"):
            self._handle_api_error(response_data)

        return response_data.get("result", {})

    def _handle_api_error(self, data: Dict[str, Any]):
        error_code = data.get("error_code", 0)
        description = data.get("description", "Unknown error")
        parameters = data.get("parameters", {})

        logger.warning(f"Telegram API Error {error_code}: {description}")

        if error_code == 429:
            retry_after = parameters.get("retry_after", 5)
            raise TelegramRateLimitError(error_code, description, parameters, retry_after=retry_after)

        if error_code == 403:
            raise TelegramForbiddenError(error_code, description, parameters)

        raise TelegramApiError(error_code, description, parameters)