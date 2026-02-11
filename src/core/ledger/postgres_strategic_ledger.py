import json
from typing import List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.domain.strategic_context import StrategicContext
from src.core.ledger.strategic_event import StrategicEvent
from src.core.ledger.strategic_ledger import StrategicLedger


class PostgresStrategicLedger(StrategicLedger):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresStrategicLedger":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS strategic_events (
                        id UUID PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL,
                        event_type TEXT NOT NULL,
                        details JSONB NOT NULL DEFAULT '{}'::jsonb,
                        country TEXT NOT NULL,
                        region TEXT NULL,
                        goal_id TEXT NULL,
                        domain TEXT NOT NULL,
                        context_key TEXT NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_strategic_events_context_time
                    ON strategic_events (context_key, timestamp ASC)
                    """
                )
            )

    def record(self, event: StrategicEvent) -> None:
        context = event.context
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO strategic_events (
                        id, timestamp, event_type, details,
                        country, region, goal_id, domain, context_key
                    )
                    VALUES (
                        :id, :timestamp, :event_type, :details::jsonb,
                        :country, :region, :goal_id, :domain, :context_key
                    )
                    """
                ),
                {
                    "id": event.id,
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "details": json.dumps(event.details),
                    "country": context.country,
                    "region": context.region,
                    "goal_id": context.goal_id,
                    "domain": context.domain,
                    "context_key": str(context),
                },
            )

    def get_history(self, context: StrategicContext) -> List[StrategicEvent]:
        key = str(context)
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, timestamp, event_type, details
                    FROM strategic_events
                    WHERE context_key = :context_key
                    ORDER BY timestamp ASC
                    """
                ),
                {"context_key": key},
            ).fetchall()
        return [
            StrategicEvent(
                id=row.id,
                timestamp=row.timestamp,
                event_type=row.event_type,
                details=dict(row.details or {}),
                context=context,
            )
            for row in rows
        ]
