import json
from typing import List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.ledger.budget_event import BudgetEvent
from src.core.ledger.budget_ledger import BudgetLedger


class PostgresBudgetLedger(BudgetLedger):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresBudgetLedger":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS budget_events (
                        id UUID PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL,
                        event_type TEXT NOT NULL,
                        delta JSONB NOT NULL DEFAULT '{}'::jsonb,
                        reason TEXT NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_budget_events_timestamp
                    ON budget_events (timestamp ASC)
                    """
                )
            )

    def record(self, event: BudgetEvent) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO budget_events (id, timestamp, event_type, delta, reason)
                    VALUES (:id, :timestamp, :event_type, :delta::jsonb, :reason)
                    """
                ),
                {
                    "id": event.id,
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "delta": json.dumps(event.delta),
                    "reason": event.reason,
                },
            )

    def get_history(self) -> List[BudgetEvent]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, timestamp, event_type, delta, reason
                    FROM budget_events
                    ORDER BY timestamp ASC
                    """
                )
            ).fetchall()
        return [
            BudgetEvent(
                id=row.id,
                timestamp=row.timestamp,
                event_type=row.event_type,
                delta=dict(row.delta or {}),
                reason=row.reason,
            )
            for row in rows
        ]
