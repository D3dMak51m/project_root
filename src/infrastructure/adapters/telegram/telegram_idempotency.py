import time
from typing import Dict, Tuple
from uuid import UUID

class TelegramIdempotencyCache:
    """
    Simple in-memory TTL cache for idempotency keys.
    Prevents duplicate execution of the same intent.
    """
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        # Key: intent_id (UUID), Value: (timestamp, result_metadata)
        self._cache: Dict[UUID, Tuple[float, dict]] = {}

    def is_processed(self, intent_id: UUID) -> bool:
        self._cleanup()
        return intent_id in self._cache

    def mark_processed(self, intent_id: UUID, metadata: dict = None) -> None:
        self._cache[intent_id] = (time.time(), metadata or {})

    def get_metadata(self, intent_id: UUID) -> dict:
        if intent_id in self._cache:
            return self._cache[intent_id][1]
        return {}

    def _cleanup(self):
        now = time.time()
        keys_to_remove = [
            k for k, (ts, _) in self._cache.items()
            if now - ts > self.ttl_seconds
        ]
        for k in keys_to_remove:
            del self._cache[k]