from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, Any
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.resource import ResourceCost


class OutboundIntentFactory:
    """
    Factory for creating valid ExecutionIntents for Telegram.
    Ensures all required constraints and metadata are present.
    """

    def create_telegram_intent(
            self,
            commitment_id: str,  # UUID string
            intention_id: str,  # UUID string
            persona_id: str,  # UUID string
            target_chat_id: str,
            text: str,
            risk_level: float = 0.1
    ) -> ExecutionIntent:
        now = datetime.now(timezone.utc)

        # Default cost for a message
        cost = ResourceCost(
            energy_cost=1.0,
            attention_cost=1.0,
            execution_slot_cost=1
        )

        constraints = {
            "platform": "telegram",
            "target_id": target_chat_id,
            "text": text
        }

        from uuid import UUID
        return ExecutionIntent(
            id=uuid4(),
            commitment_id=UUID(commitment_id),
            intention_id=UUID(intention_id),
            persona_id=UUID(persona_id),
            abstract_action="communicate",
            constraints=constraints,
            created_at=now,
            reversible=False,
            risk_level=risk_level,
            estimated_cost=cost
        )