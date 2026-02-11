from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.domain.strategic_context import StrategicContext
from src.core.persistence.strategic_state_backend import StrategicStateBackend
from src.core.persistence.strategic_state_bundle import StrategicStateBundle
from src.persistence.postgres.pickle_codec import decode_payload, encode_payload


class PostgresStrategicStateBackend(StrategicStateBackend):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresStrategicStateBackend":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS strategic_state_bundles (
                        context_key TEXT PRIMARY KEY,
                        country TEXT NOT NULL,
                        region TEXT NULL,
                        goal_id TEXT NULL,
                        domain TEXT NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        payload BYTEA NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_strategic_state_domain
                    ON strategic_state_bundles (domain)
                    """
                )
            )

    def load(self, context: StrategicContext) -> Optional[StrategicStateBundle]:
        key = str(context)
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT payload
                    FROM strategic_state_bundles
                    WHERE context_key = :context_key
                    """
                ),
                {"context_key": key},
            ).first()
        if not row:
            return None
        return decode_payload(row.payload)

    def save(self, context: StrategicContext, bundle: StrategicStateBundle) -> None:
        key = str(context)
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO strategic_state_bundles (
                        context_key,
                        country,
                        region,
                        goal_id,
                        domain,
                        updated_at,
                        payload
                    )
                    VALUES (
                        :context_key,
                        :country,
                        :region,
                        :goal_id,
                        :domain,
                        :updated_at,
                        :payload
                    )
                    ON CONFLICT (context_key)
                    DO UPDATE SET
                      country = EXCLUDED.country,
                      region = EXCLUDED.region,
                      goal_id = EXCLUDED.goal_id,
                      domain = EXCLUDED.domain,
                      updated_at = EXCLUDED.updated_at,
                      payload = EXCLUDED.payload
                    """
                ),
                {
                    "context_key": key,
                    "country": context.country,
                    "region": context.region,
                    "goal_id": context.goal_id,
                    "domain": context.domain,
                    "updated_at": datetime.now(timezone.utc),
                    "payload": encode_payload(bundle),
                },
            )
