from typing import List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.store.counterfactual_memory_store import CounterfactualMemoryStore
from src.persistence.postgres.pickle_codec import decode_payload, encode_payload


class PostgresCounterfactualMemoryStore(CounterfactualMemoryStore):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresCounterfactualMemoryStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS counterfactual_events (
                        id UUID PRIMARY KEY,
                        context_domain TEXT NOT NULL,
                        intent_id UUID NOT NULL,
                        ts TIMESTAMPTZ NOT NULL,
                        payload BYTEA NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_counterfactual_context_time
                    ON counterfactual_events (context_domain, ts DESC)
                    """
                )
            )

    def append(self, event: CounterfactualEvent) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO counterfactual_events (id, context_domain, intent_id, ts, payload)
                    VALUES (:id, :context_domain, :intent_id, :ts, :payload)
                    """
                ),
                {
                    "id": event.id,
                    "context_domain": event.context_domain,
                    "intent_id": event.intent_id,
                    "ts": event.timestamp,
                    "payload": encode_payload(event),
                },
            )

    def list_all(self) -> List[CounterfactualEvent]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT payload FROM counterfactual_events ORDER BY ts ASC")
            ).fetchall()
            return [decode_payload(row.payload) for row in rows]

    def list_by_context(self, context_domain: str) -> List[CounterfactualEvent]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT payload
                    FROM counterfactual_events
                    WHERE context_domain=:context_domain
                    ORDER BY ts ASC
                    """
                ),
                {"context_domain": context_domain},
            ).fetchall()
            return [decode_payload(row.payload) for row in rows]
