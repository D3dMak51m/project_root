import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.execution.domain.execution_result_envelope import ExecutionResultEnvelope
from src.execution.serialization import deserialize_result, serialize_result


class ExecutionResultInbox(ABC):
    @abstractmethod
    def append(self, envelope: ExecutionResultEnvelope) -> UUID:
        pass

    @abstractmethod
    def lease(self, consumer_id: str, batch: int, visibility_timeout: timedelta) -> List[Dict]:
        pass

    @abstractmethod
    def ack(self, envelope_id: UUID, consumer_id: str) -> bool:
        pass

    @abstractmethod
    def reclaim_expired(self) -> int:
        pass

    @abstractmethod
    def depth(self) -> int:
        pass


class InMemoryExecutionResultInbox(ExecutionResultInbox):
    def __init__(self):
        self._items: Dict[UUID, Dict] = {}
        self._lock = Lock()

    def append(self, envelope: ExecutionResultEnvelope) -> UUID:
        envelope_id = uuid4()
        with self._lock:
            self._items[envelope_id] = {
                "id": envelope_id,
                "job_id": envelope.job_id,
                "intent_id": envelope.intent_id,
                "context_domain": envelope.context_domain,
                "reservation_delta": dict(envelope.reservation_delta),
                "result": envelope.result,
                "received_at": envelope.received_at,
                "state": "pending",
                "leased_by": None,
                "lease_until": None,
            }
        return envelope_id

    def lease(self, consumer_id: str, batch: int, visibility_timeout: timedelta) -> List[Dict]:
        now = datetime.now(timezone.utc)
        out = []
        with self._lock:
            items = [x for x in self._items.values() if x["state"] == "pending"]
            items.sort(key=lambda x: x["received_at"])
            for item in items[:batch]:
                item["state"] = "leased"
                item["leased_by"] = consumer_id
                item["lease_until"] = now + visibility_timeout
                out.append(dict(item))
        return out

    def ack(self, envelope_id: UUID, consumer_id: str) -> bool:
        with self._lock:
            item = self._items.get(envelope_id)
            if not item:
                return False
            if item["state"] != "leased" or item["leased_by"] != consumer_id:
                return False
            item["state"] = "processed"
            return True

    def reclaim_expired(self) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        with self._lock:
            for item in self._items.values():
                if item["state"] != "leased":
                    continue
                if item["lease_until"] and item["lease_until"] < now:
                    item["state"] = "pending"
                    item["leased_by"] = None
                    item["lease_until"] = None
                    count += 1
        return count

    def depth(self) -> int:
        with self._lock:
            return len([x for x in self._items.values() if x["state"] == "pending"])


class PostgresExecutionResultInbox(ExecutionResultInbox):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresExecutionResultInbox":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS execution_result_inbox (
                        id UUID PRIMARY KEY,
                        job_id UUID NOT NULL,
                        intent_id UUID NOT NULL,
                        context_domain TEXT NOT NULL,
                        reservation_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
                        result_json JSONB NOT NULL,
                        received_at TIMESTAMPTZ NOT NULL,
                        state TEXT NOT NULL DEFAULT 'pending',
                        leased_by TEXT NULL,
                        lease_until TIMESTAMPTZ NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_execution_result_inbox_pending
                    ON execution_result_inbox (state, received_at)
                    """
                )
            )

    def append(self, envelope: ExecutionResultEnvelope) -> UUID:
        envelope_id = uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO execution_result_inbox (
                        id, job_id, intent_id, context_domain,
                        reservation_delta, result_json, received_at, state
                    )
                    VALUES (
                        :id, :job_id, :intent_id, :context_domain,
                        :reservation_delta::jsonb, :result_json::jsonb, :received_at, 'pending'
                    )
                    """
                ),
                {
                    "id": envelope_id,
                    "job_id": envelope.job_id,
                    "intent_id": envelope.intent_id,
                    "context_domain": envelope.context_domain,
                    "reservation_delta": json.dumps(envelope.reservation_delta),
                    "result_json": json.dumps(serialize_result(envelope.result)),
                    "received_at": envelope.received_at,
                },
            )
        return envelope_id

    def lease(self, consumer_id: str, batch: int, visibility_timeout: timedelta) -> List[Dict]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    WITH cte AS (
                      SELECT id
                      FROM execution_result_inbox
                      WHERE state='pending'
                      ORDER BY received_at ASC
                      FOR UPDATE SKIP LOCKED
                      LIMIT :batch
                    )
                    UPDATE execution_result_inbox i
                    SET state='leased',
                        leased_by=:consumer_id,
                        lease_until=now() + (:visibility_seconds || ' seconds')::interval
                    FROM cte
                    WHERE i.id = cte.id
                    RETURNING i.*
                    """
                ),
                {
                    "batch": batch,
                    "consumer_id": consumer_id,
                    "visibility_seconds": int(visibility_timeout.total_seconds()),
                },
            ).fetchall()
            return [
                {
                    "id": row.id,
                    "job_id": row.job_id,
                    "intent_id": row.intent_id,
                    "context_domain": row.context_domain,
                    "reservation_delta": dict(row.reservation_delta or {}),
                    "result": deserialize_result(row.result_json),
                    "received_at": row.received_at,
                }
                for row in rows
            ]

    def ack(self, envelope_id: UUID, consumer_id: str) -> bool:
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE execution_result_inbox
                    SET state='processed'
                    WHERE id=:id AND state='leased' AND leased_by=:consumer_id
                    """
                ),
                {"id": envelope_id, "consumer_id": consumer_id},
            ).rowcount
            return bool(count)

    def reclaim_expired(self) -> int:
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE execution_result_inbox
                    SET state='pending', leased_by=NULL, lease_until=NULL
                    WHERE state='leased' AND lease_until IS NOT NULL AND lease_until < now()
                    """
                )
            ).rowcount
            return int(count or 0)

    def depth(self) -> int:
        with self.engine.begin() as conn:
            value = conn.execute(
                text("SELECT COUNT(*) FROM execution_result_inbox WHERE state='pending'")
            ).scalar_one()
            return int(value)
