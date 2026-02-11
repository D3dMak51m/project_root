from datetime import datetime, timezone
from uuid import uuid4

from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.persona import PersonaMask
from src.core.domain.resource import ResourceCost
from src.infrastructure.services.telegram_persona_projection import TelegramPersonaProjectionService


def test_projection_uses_html_escape():
    service = TelegramPersonaProjectionService()
    persona = PersonaMask(
        id=uuid4(),
        human_id=uuid4(),
        platform="telegram",
        display_name="Mask",
        bio="",
        language="en",
        tone="formal",
        verbosity="medium",
        activity_rate=1.0,
        risk_tolerance=0.5,
        posting_hours=list(range(24))
    )
    intent = ExecutionIntent(
        id=uuid4(),
        commitment_id=uuid4(),
        intention_id=uuid4(),
        persona_id=persona.id,
        abstract_action="communicate",
        constraints={
            "platform": "telegram",
            "target_id": "1",
            "text": "a < b & c > d"
        },
        created_at=datetime.now(timezone.utc),
        reversible=False,
        risk_level=0.1,
        estimated_cost=ResourceCost(1.0, 1.0, 1)
    )

    payload = service.project(intent, persona)

    assert payload["text"] == "a &lt; b &amp; c &gt; d"
    assert payload["parse_mode"] == "HTML"
