import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
import uvicorn

from src.execution.logging.structured_runtime_logger import StructuredRuntimeLogger
from src.infrastructure.inbound.telegram.abuse_detector_service import AbuseDetectorService
from src.infrastructure.inbound.telegram.telegram_inbound_dedupe_store import (
    InMemoryTelegramInboundDedupeStore,
    TelegramInboundDedupeStore,
)
from src.infrastructure.inbound.telegram.telegram_webhook_security import TelegramWebhookSecurityService
from src.infrastructure.inbound.telegram.telegram_update_dto import RawTelegramUpdate
from src.infrastructure.inbound.telegram.telegram_normalizer import TelegramUpdateNormalizer
from src.infrastructure.observability.anomaly_hook import AnomalyHook, NoopAnomalyHook
from src.interaction.services.interaction_ingestion_service import InteractionIngestionService
from src.interaction.services.interaction_autonomy_bridge import InteractionAutonomyBridge

app = FastAPI()

# Dependencies (Injected in real app)
normalizer: TelegramUpdateNormalizer = None  # type: ignore
ingestion_service: InteractionIngestionService = None  # type: ignore
autonomy_bridge: InteractionAutonomyBridge = None  # type: ignore
secret_token_value: str = "default_secret"
telegram_bot_id: str = "default-bot"
stale_update_window_seconds: int = 600
security_service = TelegramWebhookSecurityService(secret_token_value)
dedupe_store: TelegramInboundDedupeStore = InMemoryTelegramInboundDedupeStore()
abuse_detector: AbuseDetectorService = AbuseDetectorService()
anomaly_hook: AnomalyHook = NoopAnomalyHook()
runtime_logger = StructuredRuntimeLogger()


def setup_dependencies(
    norm,
    ingest,
    bridge,
    token,
    bot_id: str = "default-bot",
    dedupe: Optional[TelegramInboundDedupeStore] = None,
    abuse: Optional[AbuseDetectorService] = None,
    anomaly: Optional[AnomalyHook] = None,
    logger: Optional[StructuredRuntimeLogger] = None,
    stale_window_seconds: int = 600,
):
    global normalizer, ingestion_service, autonomy_bridge, secret_token_value
    global security_service, dedupe_store, abuse_detector, anomaly_hook, runtime_logger
    global telegram_bot_id, stale_update_window_seconds
    normalizer = norm
    ingestion_service = ingest
    autonomy_bridge = bridge
    secret_token_value = token
    telegram_bot_id = bot_id
    stale_update_window_seconds = int(stale_window_seconds)
    security_service = TelegramWebhookSecurityService(secret_token_value)
    dedupe_store = dedupe or InMemoryTelegramInboundDedupeStore()
    abuse_detector = abuse or AbuseDetectorService()
    anomaly_hook = anomaly or NoopAnomalyHook()
    runtime_logger = logger or StructuredRuntimeLogger()


def _extract_update_timestamp(payload: dict) -> Optional[datetime]:
    for key in ("message", "edited_message", "channel_post"):
        item = payload.get(key)
        if isinstance(item, dict) and item.get("date") is not None:
            try:
                return datetime.fromtimestamp(int(item["date"]), tz=timezone.utc)
            except Exception:
                return None
    return None


@app.post("/telegram/webhook")
async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    # 1. Security Check
    token = x_telegram_bot_api_secret_token or ""
    if not security_service.verify_token(token):
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # 2. Parse Body
    try:
        raw_body = await request.body()
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    payload_hash = security_service.payload_hash(raw_body)

    # 3. Replay protection + dedupe
    if "update_id" not in payload:
        runtime_logger.emit(event_type="WEBHOOK_IGNORED", status="ignored_no_update_id")
        return {"status": "ignored"}
    update_id = int(payload["update_id"])
    if not dedupe_store.mark_if_new(telegram_bot_id, update_id, payload_hash):
        runtime_logger.emit(
            event_type="WEBHOOK_DUPLICATE",
            status="duplicate",
            update_id=update_id,
            bot_id=telegram_bot_id,
        )
        return {"status": "duplicate"}

    # 4. Stale update policy
    observed_at = _extract_update_timestamp(payload)
    if observed_at is not None and stale_update_window_seconds > 0:
        if datetime.now(timezone.utc) - observed_at > timedelta(seconds=stale_update_window_seconds):
            runtime_logger.emit(
                event_type="WEBHOOK_STALE",
                status="stale",
                update_id=update_id,
                bot_id=telegram_bot_id,
            )
            return {"status": "stale"}

    raw_update = RawTelegramUpdate(
        update_id=update_id,
        payload=payload,
        secret_token=x_telegram_bot_api_secret_token
    )

    # 5. Normalize
    event = normalizer.normalize(raw_update)

    if event:
        try:
            anomaly_hook.on_inbound(event)
        except Exception:
            pass

        decision = abuse_detector.evaluate(event)
        if decision.throttled and event.message_type != "command":
            runtime_logger.emit(
                event_type="ABUSE_THROTTLED_USER",
                status="throttled",
                reason=decision.reason,
                update_id=update_id,
                user_id=event.user_id,
                chat_id=event.chat_id,
            )
            return {"status": "throttled"}

        # 6. Ingest (Memory + Buffer)
        ingestion_service.ingest(event)

        # 7. Bridge (Telemetry only)
        autonomy_bridge.process_interaction(event)

    runtime_logger.emit(
        event_type="WEBHOOK_OK",
        status="ok",
        update_id=update_id,
        bot_id=telegram_bot_id,
    )

    # 8. Always return 200 OK
    return {"status": "ok"}


def run_server(host="0.0.0.0", port=8000):
    uvicorn.run(app, host=host, port=port)
