from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.persistence.postgres.pickle_codec import decode_payload, encode_payload
from src.world.context.context_buffer import ContextBuffer
from src.world.domain.world_observation import WorldObservation


class PostgresContextBuffer(ContextBuffer):
    """
    Durable context buffer with SKIP LOCKED pop semantics.
    """

    def __init__(self, engine: Engine, pop_limit: int = 1000):
        super().__init__()
        self.engine = engine
        self.pop_limit = pop_limit
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str, pop_limit: int = 1000) -> "PostgresContextBuffer":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine, pop_limit=pop_limit)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS context_buffer (
                        id UUID PRIMARY KEY,
                        context_domain TEXT NULL,
                        observed_at TIMESTAMPTZ NOT NULL,
                        payload BYTEA NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_context_buffer_context_time
                    ON context_buffer (context_domain, observed_at DESC)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_context_buffer_observed_at
                    ON context_buffer (observed_at ASC)
                    """
                )
            )

    def add(self, observation: WorldObservation) -> None:
        observed_at = datetime.now(timezone.utc)
        if observation.interaction and observation.interaction.timestamp:
            observed_at = observation.interaction.timestamp
        elif observation.signal and getattr(observation.signal, "timestamp", None):
            observed_at = observation.signal.timestamp

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO context_buffer (id, context_domain, observed_at, payload)
                    VALUES (:id, :context_domain, :observed_at, :payload)
                    """
                ),
                {
                    "id": uuid4(),
                    "context_domain": observation.context_domain,
                    "observed_at": observed_at,
                    "payload": encode_payload(observation),
                },
            )

    def pop_all(self) -> List[WorldObservation]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    WITH picked AS (
                        SELECT id
                        FROM context_buffer
                        ORDER BY observed_at ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT :limit
                    )
                    DELETE FROM context_buffer cb
                    USING picked
                    WHERE cb.id = picked.id
                    RETURNING cb.payload
                    """
                ),
                {"limit": self.pop_limit},
            ).fetchall()
        return [decode_payload(row.payload) for row in rows]

    def depth(self) -> int:
        with self.engine.begin() as conn:
            value = conn.execute(text("SELECT COUNT(*) FROM context_buffer")).scalar_one()
        return int(value)
