from datetime import datetime, timezone
from typing import Optional

from src.core.interfaces.execution_adapter import ExecutionAdapter
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.integration.normalizer import ResultNormalizer
from src.infrastructure.adapters.telegram.telegram_client import TelegramClient
from src.infrastructure.adapters.telegram.telegram_errors import (
    TelegramError, TelegramRateLimitError, TelegramForbiddenError, TelegramNetworkError
)
from src.infrastructure.adapters.telegram.telegram_idempotency import TelegramIdempotencyCache
from src.integration.registry import ExecutionAdapterRegistry


# Assuming we have access to a global observer or we inject it.
# For T3 compliance "Admin Telemetry", the adapter should ideally emit telemetry.
# However, ExecutionAdapter interface doesn't include observer.
# Telemetry is usually handled by the Orchestrator upon receiving the result.
# But T3 prompt says "Admin Telemetry: ... TELEGRAM_MESSAGE_SENT ...".
# If this is a specific event type, the Orchestrator emits it based on result.
# Or the adapter includes it in observations.
# We will include specific flags in observations for the Orchestrator/Observer to pick up.

class TelegramExecutionAdapter(ExecutionAdapter):
    """
    Outbound-only execution adapter for Telegram.
    Translates ExecutionIntent into Telegram API calls.
    Enforces idempotency and handles platform-specific errors.
    """

    def __init__(self, token: str, default_chat_id: Optional[str] = None):
        self.client = TelegramClient(token)
        self.default_chat_id = default_chat_id
        self.idempotency = TelegramIdempotencyCache()

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        # 1. Idempotency Check
        if self.idempotency.is_processed(intent.id):
            return ResultNormalizer.success(
                effects=["message_deduplicated"],
                costs={"api_calls": 0.0},
                observations={"deduplicated": True, "original_meta": self.idempotency.get_metadata(intent.id)}
            )

        # 2. Validate Intent Platform
        if intent.constraints.get("platform") != "telegram":
            return ResultNormalizer.rejection(
                reason=f"Invalid platform for TelegramAdapter: {intent.constraints.get('platform')}"
            )

        # 3. Extract Payload
        text = intent.constraints.get("text")
        target_id = intent.constraints.get("target_id") or self.default_chat_id
        parse_mode = intent.constraints.get("parse_mode")  # Optional, from projection service

        if not text:
            return ResultNormalizer.failure(
                reason="No text content provided in intent constraints",
                failure_type=ExecutionFailureType.INTERNAL
            )

        if not target_id:
            return ResultNormalizer.failure(
                reason="No target_id provided for Telegram message",
                failure_type=ExecutionFailureType.INTERNAL
            )

        # 4. Execute via Client
        try:
            result = self.client.send_message(
                chat_id=target_id,
                text=text,
                parse_mode=parse_mode
            )

            self.idempotency.mark_processed(intent.id, {"message_id": result.get("message_id")})

            return ResultNormalizer.success(
                effects=["message_sent"],
                costs={"api_calls": 1.0},
                observations={
                    "message_id": result.get("message_id"),
                    "telemetry_event": "TELEGRAM_MESSAGE_SENT"  # Hint for observer
                }
            )

        except TelegramRateLimitError as e:
            return ResultNormalizer.failure(
                reason=f"Rate limit exceeded. Retry after {e.retry_after}s",
                failure_type=ExecutionFailureType.ENVIRONMENT,
                costs={"api_calls": 1.0}
            )

        except TelegramForbiddenError as e:
            return ResultNormalizer.failure(
                reason=f"Bot blocked by user: {e.description}",
                failure_type=ExecutionFailureType.POLICY,
                costs={"api_calls": 1.0}
            )

        except TelegramNetworkError as e:
            return ResultNormalizer.failure(
                reason=f"Network error: {str(e)}",
                failure_type=ExecutionFailureType.ENVIRONMENT
            )

        except TelegramError as e:
            return ResultNormalizer.failure(
                reason=f"Telegram API error: {str(e)}",
                failure_type=ExecutionFailureType.ENVIRONMENT,
                costs={"api_calls": 1.0},
                timestamp=None  # Normalizer handles timestamp
            )

        except Exception as e:
            return ResultNormalizer.failure(
                reason=f"Unexpected adapter error: {str(e)}",
                failure_type=ExecutionFailureType.INTERNAL
            )


# Explicit Registration
def register_telegram_adapter(token: str, default_chat_id: Optional[str] = None):
    registry = ExecutionAdapterRegistry.get_global()
    registry.register("telegram", TelegramExecutionAdapter(token, default_chat_id))