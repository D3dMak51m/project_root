from datetime import datetime, timezone
from uuid import uuid4

from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.resource import ResourceCost
from src.infrastructure.adapters.telegram.telegram_execution_adapter import TelegramExecutionAdapter


def test_telegram_adapter_success_does_not_emit_telemetry_observation():
    adapter = TelegramExecutionAdapter(token="test-token", default_chat_id="42")
    adapter.client.send_message = lambda chat_id, text, parse_mode=None: {"message_id": 12345}

    intent = ExecutionIntent(
        id=uuid4(),
        commitment_id=uuid4(),
        intention_id=uuid4(),
        persona_id=uuid4(),
        abstract_action="communicate",
        constraints={
            "platform": "telegram",
            "target_id": "42",
            "text": "hello",
            "parse_mode": "HTML"
        },
        created_at=datetime.now(timezone.utc),
        reversible=False,
        risk_level=0.1,
        estimated_cost=ResourceCost(1.0, 1.0, 1)
    )

    result = adapter.execute(intent)

    assert result.status.value == "SUCCESS"
    assert "message_id" in result.observations
    assert "telemetry_event" not in result.observations
