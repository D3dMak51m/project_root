from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.persistence.postgres.pickle_codec import decode_payload, encode_payload
from src.world.domain.world_observation import WorldObservation
from src.world.store.world_observation_store import WorldObservationStore


class PostgresWorldObservationStore(WorldObservationStore):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresWorldObservationStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS world_observations (
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
                    CREATE INDEX IF NOT EXISTS ix_world_observations_context_time
                    ON world_observations (context_domain, observed_at DESC)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_world_observations_time
                    ON world_observations (observed_at DESC)
                    """
                )
            )

    def append(self, observation: WorldObservation) -> None:
        observed_at = datetime.now(timezone.utc)
        if observation.interaction and observation.interaction.timestamp:
            observed_at = observation.interaction.timestamp
        elif observation.signal and getattr(observation.signal, "timestamp", None):
            observed_at = observation.signal.timestamp

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO world_observations (id, context_domain, observed_at, payload)
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

    def list_all(self) -> List[WorldObservation]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT payload FROM world_observations ORDER BY observed_at ASC")
            ).fetchall()
        return [decode_payload(row.payload) for row in rows]

    def list_by_context(self, context_domain: str, limit: int = 100) -> List[WorldObservation]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT payload
                    FROM world_observations
                    WHERE context_domain = :context_domain
                    ORDER BY observed_at DESC
                    LIMIT :limit
                    """
                ),
                {"context_domain": context_domain, "limit": limit},
            ).fetchall()
        decoded = [decode_payload(row.payload) for row in rows]
        decoded.reverse()
        return decoded
