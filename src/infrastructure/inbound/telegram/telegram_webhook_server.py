from fastapi import FastAPI, Request, Header, HTTPException
from typing import Optional
import uvicorn

from src.infrastructure.inbound.telegram.telegram_update_dto import RawTelegramUpdate
from src.infrastructure.inbound.telegram.telegram_normalizer import TelegramUpdateNormalizer
from src.interaction.services.interaction_ingestion_service import InteractionIngestionService
from src.interaction.services.interaction_autonomy_bridge import InteractionAutonomyBridge

app = FastAPI()

# Dependencies (Injected in real app)
normalizer: TelegramUpdateNormalizer = None  # type: ignore
ingestion_service: InteractionIngestionService = None  # type: ignore
autonomy_bridge: InteractionAutonomyBridge = None  # type: ignore
secret_token_value: str = "default_secret"


def setup_dependencies(norm, ingest, bridge, token):
    global normalizer, ingestion_service, autonomy_bridge, secret_token_value
    normalizer = norm
    ingestion_service = ingest
    autonomy_bridge = bridge
    secret_token_value = token


@app.post("/telegram/webhook")
async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    # 1. Security Check
    if x_telegram_bot_api_secret_token != secret_token_value:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # 2. Parse Body
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 3. Create DTO
    if "update_id" not in payload:
        return {"status": "ignored"}

    raw_update = RawTelegramUpdate(
        update_id=payload["update_id"],
        payload=payload,
        secret_token=x_telegram_bot_api_secret_token
    )

    # 4. Normalize
    event = normalizer.normalize(raw_update)

    if event:
        # 5. Ingest (Memory + Buffer)
        ingestion_service.ingest(event)

        # 6. Bridge (Telemetry only)
        autonomy_bridge.process_interaction(event)

    # 7. Always return 200 OK
    return {"status": "ok"}


def run_server(host="0.0.0.0", port=8000):
    uvicorn.run(app, host=host, port=port)