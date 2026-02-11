from typing import List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.memory.domain.event_record import EventRecord
from src.memory.store.memory_store import MemoryStore
from src.persistence.postgres.pickle_codec import decode_payload, encode_payload


class PostgresMemoryStore(MemoryStore):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresMemoryStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS memory_events (
                        id UUID PRIMARY KEY,
                        context_domain TEXT NOT NULL,
                        intent_id UUID NOT NULL,
                        issued_at TIMESTAMPTZ NOT NULL,
                        payload BYTEA NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_memory_events_context_time
                    ON memory_events (context_domain, issued_at DESC)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_memory_events_intent
                    ON memory_events (intent_id)
                    """
                )
            )

    def append(self, event: EventRecord) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO memory_events (id, context_domain, intent_id, issued_at, payload)
                    VALUES (:id, :context_domain, :intent_id, :issued_at, :payload)
                    """
                ),
                {
                    "id": event.id,
                    "context_domain": event.context_domain,
                    "intent_id": event.intent_id,
                    "issued_at": event.issued_at,
                    "payload": encode_payload(event),
                },
            )

    def list_all(self) -> List[EventRecord]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT payload FROM memory_events ORDER BY issued_at ASC")
            ).fetchall()
            return [decode_payload(row.payload) for row in rows]

    def list_by_context(self, context_domain: str, limit: int = 100) -> List[EventRecord]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT payload
                    FROM memory_events
                    WHERE context_domain=:context_domain
                    ORDER BY issued_at DESC
                    LIMIT :limit
                    """
                ),
                {"context_domain": context_domain, "limit": limit},
            ).fetchall()
            return [decode_payload(row.payload) for row in rows]
