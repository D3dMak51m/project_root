import json
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.execution.safety.circuit_breaker import CircuitTransition


class PostgresExecutionSafetyStore:
    """
    Persistence sink for runtime safety telemetry:
    - circuit breaker transitions
    - periodic rate limiter snapshots
    """

    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresExecutionSafetyStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS execution_circuit_transitions (
                        id UUID PRIMARY KEY,
                        circuit_key TEXT NOT NULL,
                        previous_state TEXT NOT NULL,
                        current_state TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        happened_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_execution_circuit_transitions_key_time
                    ON execution_circuit_transitions (circuit_key, happened_at DESC)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS execution_rate_limit_snapshots (
                        id UUID PRIMARY KEY,
                        captured_at TIMESTAMPTZ NOT NULL,
                        payload JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
            )

    def record_transition(self, transition: CircuitTransition) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO execution_circuit_transitions (
                        id, circuit_key, previous_state, current_state, reason, happened_at
                    )
                    VALUES (
                        :id, :circuit_key, :previous_state, :current_state, :reason, :happened_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "circuit_key": transition.key,
                    "previous_state": transition.previous.value,
                    "current_state": transition.current.value,
                    "reason": transition.reason,
                    "happened_at": transition.at,
                },
            )

    def record_rate_limit_snapshot(self, snapshot: Dict[str, int]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO execution_rate_limit_snapshots (id, captured_at, payload)
                    VALUES (:id, :captured_at, :payload::jsonb)
                    """
                ),
                {
                    "id": uuid4(),
                    "captured_at": datetime.now(timezone.utc),
                    "payload": json.dumps(snapshot),
                },
            )
