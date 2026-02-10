from typing import Dict, Any
from src.integration.adapters.base import BasePlatformAdapter
from src.interaction.domain.intent import InteractionIntent, InteractionType
from src.core.domain.execution_result import ExecutionResult, ExecutionFailureType
from src.integration.normalizer import ResultNormalizer


class TelegramAdapter(BasePlatformAdapter):
    """
    Stub implementation for Telegram interaction.
    """

    def _perform_execution(self, intent: InteractionIntent) -> ExecutionResult:
        # 1. Validate Intent Compatibility
        if intent.type != InteractionType.MESSAGE:
            return ResultNormalizer.rejection("TelegramAdapter only supports MESSAGE type")

        # 2. Simulate API Call (Mock)
        try:
            success = True

            if success:
                return ResultNormalizer.success(
                    effects=["message_sent"],
                    costs={"energy": 1.0, "api_calls": 1.0},
                    observations={"message_id": "12345"}
                )
            else:
                return ResultNormalizer.failure(
                    reason="Telegram API timeout",
                    failure_type=ExecutionFailureType.ENVIRONMENT
                )

        except Exception as e:
            return ResultNormalizer.failure(
                reason=f"Telegram API Error: {str(e)}",
                failure_type=ExecutionFailureType.ENVIRONMENT
            )