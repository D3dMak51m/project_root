from datetime import datetime, timezone
from typing import Optional

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from src.infrastructure.inbound.telegram.abuse_detector_service import AbuseDetectorService
from src.infrastructure.inbound.telegram.telegram_inbound_dedupe_store import (
    InMemoryTelegramInboundDedupeStore,
)
from src.infrastructure.inbound.telegram.telegram_normalizer import TelegramUpdateNormalizer
from src.infrastructure.inbound.telegram.telegram_webhook_server import app, setup_dependencies


class _Ingestion:
    def __init__(self):
        self.events = []

    def ingest(self, event):
        self.events.append(event)


class _Bridge:
    def process_interaction(self, event):
        return


def _payload(update_id: int, text: str = "hello") -> dict:
    return {
        "update_id": update_id,
        "message": {
            "date": int(datetime.now(timezone.utc).timestamp()),
            "text": text,
            "from": {"id": 1001},
            "chat": {"id": 2001},
        },
    }


def _client(secret: str = "secret-token", abuse: Optional[AbuseDetectorService] = None):
    setup_dependencies(
        norm=TelegramUpdateNormalizer(),
        ingest=_Ingestion(),
        bridge=_Bridge(),
        token=secret,
        bot_id="bot-A",
        dedupe=InMemoryTelegramInboundDedupeStore(),
        abuse=abuse,
    )
    return TestClient(app)


def test_webhook_duplicate_update_is_replay_safe():
    client = _client()
    headers = {"x-telegram-bot-api-secret-token": "secret-token"}

    first = client.post("/telegram/webhook", json=_payload(10), headers=headers)
    second = client.post("/telegram/webhook", json=_payload(10), headers=headers)

    assert first.status_code == 200
    assert first.json()["status"] == "ok"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"


def test_webhook_rejects_invalid_secret_token():
    client = _client()
    response = client.post(
        "/telegram/webhook",
        json=_payload(11),
        headers={"x-telegram-bot-api-secret-token": "wrong"},
    )
    assert response.status_code == 403


def test_abuse_soft_throttle_preserves_commands():
    abuse = AbuseDetectorService(per_user_limit=0, per_chat_limit=0, window_seconds=60)
    client = _client(abuse=abuse)
    headers = {"x-telegram-bot-api-secret-token": "secret-token"}

    throttled = client.post("/telegram/webhook", json=_payload(12, text="hello"), headers=headers)
    command = client.post("/telegram/webhook", json=_payload(13, text="/help"), headers=headers)

    assert throttled.status_code == 200
    assert throttled.json()["status"] == "throttled"
    assert command.status_code == 200
    assert command.json()["status"] == "ok"
