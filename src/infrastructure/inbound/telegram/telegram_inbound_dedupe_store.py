from abc import ABC, abstractmethod
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class TelegramInboundDedupeStore(ABC):
    @abstractmethod
    def mark_if_new(self, bot_id: str, update_id: int, payload_hash: str) -> bool:
        pass


class InMemoryTelegramInboundDedupeStore(TelegramInboundDedupeStore):
    def __init__(self):
        self._seen: Dict[Tuple[str, int], str] = {}
        self._lock = Lock()

    def mark_if_new(self, bot_id: str, update_id: int, payload_hash: str) -> bool:
        key = (bot_id, int(update_id))
        with self._lock:
            if key in self._seen:
                return False
            self._seen[key] = payload_hash
            return True


class PostgresTelegramInboundDedupeStore(TelegramInboundDedupeStore):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresTelegramInboundDedupeStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS telegram_inbound_updates (
                        bot_id TEXT NOT NULL,
                        update_id BIGINT NOT NULL,
                        payload_hash TEXT NOT NULL,
                        received_at TIMESTAMPTZ NOT NULL,
                        PRIMARY KEY (bot_id, update_id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_telegram_inbound_updates_received
                    ON telegram_inbound_updates (received_at DESC)
                    """
                )
            )

    def mark_if_new(self, bot_id: str, update_id: int, payload_hash: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO telegram_inbound_updates (bot_id, update_id, payload_hash, received_at)
                    VALUES (:bot_id, :update_id, :payload_hash, :received_at)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "bot_id": bot_id,
                    "update_id": int(update_id),
                    "payload_hash": payload_hash,
                    "received_at": datetime.now(timezone.utc),
                },
            )
            return bool(result.rowcount)

