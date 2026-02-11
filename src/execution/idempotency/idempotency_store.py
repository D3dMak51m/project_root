from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class IdempotencyState(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass(frozen=True)
class IdempotencyRecord:
    intent_id: UUID
    state: IdempotencyState
    updated_at: datetime
    result_metadata: Dict


class IdempotencyStore(ABC):
    @abstractmethod
    def begin(self, intent_id: UUID) -> IdempotencyState:
        pass

    @abstractmethod
    def complete(self, intent_id: UUID, metadata: Optional[Dict] = None) -> None:
        pass

    @abstractmethod
    def clear_in_progress(self, intent_id: UUID) -> None:
        pass

    @abstractmethod
    def get(self, intent_id: UUID) -> Optional[IdempotencyRecord]:
        pass


class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self):
        self._records: Dict[UUID, IdempotencyRecord] = {}
        self._lock = Lock()

    def begin(self, intent_id: UUID) -> IdempotencyState:
        now = datetime.now(timezone.utc)
        with self._lock:
            record = self._records.get(intent_id)
            if not record:
                self._records[intent_id] = IdempotencyRecord(
                    intent_id=intent_id,
                    state=IdempotencyState.IN_PROGRESS,
                    updated_at=now,
                    result_metadata={},
                )
                return IdempotencyState.NEW
            if record.state == IdempotencyState.DONE:
                return IdempotencyState.DONE
            return IdempotencyState.IN_PROGRESS

    def complete(self, intent_id: UUID, metadata: Optional[Dict] = None) -> None:
        with self._lock:
            self._records[intent_id] = IdempotencyRecord(
                intent_id=intent_id,
                state=IdempotencyState.DONE,
                updated_at=datetime.now(timezone.utc),
                result_metadata=metadata or {},
            )

    def clear_in_progress(self, intent_id: UUID) -> None:
        with self._lock:
            record = self._records.get(intent_id)
            if not record:
                return
            if record.state == IdempotencyState.IN_PROGRESS:
                del self._records[intent_id]

    def get(self, intent_id: UUID) -> Optional[IdempotencyRecord]:
        with self._lock:
            return self._records.get(intent_id)


class PostgresIdempotencyStore(IdempotencyStore):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresIdempotencyStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS execution_idempotency (
                        intent_id UUID NOT NULL,
                        partition_year INTEGER NOT NULL,
                        state TEXT NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        result_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        PRIMARY KEY (intent_id, partition_year)
                    ) PARTITION BY RANGE (partition_year)
                    """
                )
            )
            self._ensure_partition(conn, datetime.now(timezone.utc).year)
            self._ensure_partition(conn, datetime.now(timezone.utc).year + 1)
            try:
                conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_execution_idempotency_intent_hash
                        ON execution_idempotency USING HASH (intent_id)
                        """
                    )
                )
            except Exception:
                conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS ix_execution_idempotency_intent_btree
                        ON execution_idempotency (intent_id)
                        """
                    )
                )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_execution_idempotency_updated_at
                    ON execution_idempotency (updated_at)
                    """
                )
            )

    def _ensure_partition(self, conn, year: int) -> None:
        table_name = f"execution_idempotency_y{year}"
        try:
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name}
                    PARTITION OF execution_idempotency
                    FOR VALUES FROM ({year}) TO ({year + 1})
                    """
                )
            )
        except Exception:
            # Backward compatibility: existing non-partitioned table.
            return

    def begin(self, intent_id: UUID) -> IdempotencyState:
        now = datetime.now(timezone.utc)
        year = now.year
        with self.engine.begin() as conn:
            self._ensure_partition(conn, year)
            row = conn.execute(
                text(
                    """
                    SELECT state
                    FROM execution_idempotency
                    WHERE intent_id=:intent_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ),
                {"intent_id": intent_id},
            ).first()
            if not row:
                conn.execute(
                    text(
                        """
                        INSERT INTO execution_idempotency (intent_id, partition_year, state, updated_at)
                        VALUES (:intent_id, :partition_year, :state, :updated_at)
                        """
                    ),
                    {
                        "intent_id": intent_id,
                        "partition_year": year,
                        "state": IdempotencyState.IN_PROGRESS.value,
                        "updated_at": now,
                    },
                )
                return IdempotencyState.NEW
            if row.state == IdempotencyState.DONE.value:
                return IdempotencyState.DONE
            return IdempotencyState.IN_PROGRESS

    def complete(self, intent_id: UUID, metadata: Optional[Dict] = None) -> None:
        now = datetime.now(timezone.utc)
        year = now.year
        with self.engine.begin() as conn:
            self._ensure_partition(conn, year)
            conn.execute(
                text(
                    """
                    INSERT INTO execution_idempotency (
                        intent_id, partition_year, state, updated_at, result_metadata
                    )
                    VALUES (:intent_id, :partition_year, :state, :updated_at, :result_metadata::jsonb)
                    ON CONFLICT (intent_id, partition_year)
                    DO UPDATE SET
                      state=EXCLUDED.state,
                      updated_at=EXCLUDED.updated_at,
                      result_metadata=EXCLUDED.result_metadata
                    """
                ),
                {
                    "intent_id": intent_id,
                    "partition_year": year,
                    "state": IdempotencyState.DONE.value,
                    "updated_at": now,
                    "result_metadata": metadata or {},
                },
            )

    def clear_in_progress(self, intent_id: UUID) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM execution_idempotency
                    WHERE intent_id=:intent_id AND state=:state
                    """
                ),
                {"intent_id": intent_id, "state": IdempotencyState.IN_PROGRESS.value},
            )

    def get(self, intent_id: UUID) -> Optional[IdempotencyRecord]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT intent_id, state, updated_at, result_metadata
                    FROM execution_idempotency
                    WHERE intent_id=:intent_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ),
                {"intent_id": intent_id},
            ).first()
            if not row:
                return None
            return IdempotencyRecord(
                intent_id=row.intent_id,
                state=IdempotencyState(row.state),
                updated_at=row.updated_at,
                result_metadata=dict(row.result_metadata or {}),
            )
