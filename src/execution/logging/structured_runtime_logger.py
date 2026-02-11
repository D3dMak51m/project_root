import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredRuntimeLogger:
    """
    Lightweight JSON-lines logger for worker/dispatcher/webhook paths.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or logging.getLogger("runtime")

    def emit(self, event_type: str, **fields: Any) -> None:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
        }
        payload.update(fields)
        self._logger.info(json.dumps(payload, default=str, ensure_ascii=True))

