import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.execution.domain.execution_job import DlqState, ExecutionJob, ExecutionJobState
from src.execution.queue.execution_queue import ExecutionQueue
from src.execution.serialization import deserialize_intent, serialize_intent


class PostgresExecutionQueue(ExecutionQueue):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresExecutionQueue":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS execution_jobs (
                        id UUID PRIMARY KEY,
                        intent_id UUID NOT NULL,
                        intent_json JSONB NOT NULL,
                        context_domain TEXT NOT NULL,
                        reservation_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
                        state TEXT NOT NULL,
                        priority DOUBLE PRECISION NOT NULL DEFAULT 0,
                        available_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        leased_by TEXT NULL,
                        lease_until TIMESTAMPTZ NULL,
                        attempt_count INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 5,
                        last_error TEXT NULL,
                        job_version INTEGER NOT NULL DEFAULT 1,
                        parent_job_id UUID NULL,
                        dlq_state TEXT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_execution_jobs_intent_active
                    ON execution_jobs (intent_id)
                    WHERE state IN ('queued', 'leased')
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_execution_jobs_queue_scan
                    ON execution_jobs (state, available_at, priority DESC, created_at ASC)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS execution_dlq_events (
                        id UUID PRIMARY KEY,
                        job_id UUID NOT NULL,
                        event_type TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        payload JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
            )

    def _row_to_job(self, row) -> ExecutionJob:
        reservation_delta = row.reservation_delta or {}
        return ExecutionJob(
            id=row.id,
            intent=deserialize_intent(row.intent_json),
            context_domain=row.context_domain,
            reservation_delta=dict(reservation_delta),
            state=ExecutionJobState(row.state),
            priority=float(row.priority),
            available_at=row.available_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            leased_by=row.leased_by,
            lease_until=row.lease_until,
            attempt_count=int(row.attempt_count),
            max_attempts=int(row.max_attempts),
            last_error=row.last_error,
            job_version=int(row.job_version),
            parent_job_id=row.parent_job_id,
            dlq_state=DlqState(row.dlq_state) if row.dlq_state else None,
        )

    def enqueue(self, job: ExecutionJob) -> UUID:
        with self.engine.begin() as conn:
            existing = conn.execute(
                text(
                    """
                    SELECT id
                    FROM execution_jobs
                    WHERE intent_id = :intent_id
                    AND state IN ('queued', 'leased')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"intent_id": job.intent.id},
            ).first()
            if existing:
                return existing.id

            conn.execute(
                text(
                    """
                    INSERT INTO execution_jobs (
                        id, intent_id, intent_json, context_domain, reservation_delta,
                        state, priority, available_at, created_at, updated_at,
                        attempt_count, max_attempts, job_version, parent_job_id
                    ) VALUES (
                        :id, :intent_id, :intent_json::jsonb, :context_domain, :reservation_delta::jsonb,
                        :state, :priority, :available_at, :created_at, :updated_at,
                        :attempt_count, :max_attempts, :job_version, :parent_job_id
                    )
                    """
                ),
                {
                    "id": job.id,
                    "intent_id": job.intent.id,
                    "intent_json": json.dumps(serialize_intent(job.intent)),
                    "context_domain": job.context_domain,
                    "reservation_delta": json.dumps(job.reservation_delta),
                    "state": job.state.value,
                    "priority": job.priority,
                    "available_at": job.available_at,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "attempt_count": job.attempt_count,
                    "max_attempts": job.max_attempts,
                    "job_version": job.job_version,
                    "parent_job_id": job.parent_job_id,
                },
            )
            return job.id

    def lease(self, worker_id: str, batch: int, visibility_timeout: timedelta) -> List[ExecutionJob]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    WITH cte AS (
                      SELECT id
                      FROM execution_jobs
                      WHERE state = 'queued' AND available_at <= now()
                      ORDER BY priority DESC, created_at ASC
                      FOR UPDATE SKIP LOCKED
                      LIMIT :batch
                    )
                    UPDATE execution_jobs j
                    SET state='leased',
                        leased_by=:worker_id,
                        lease_until=now() + (:visibility_seconds || ' seconds')::interval,
                        attempt_count=attempt_count+1,
                        updated_at=now()
                    FROM cte
                    WHERE j.id = cte.id
                    RETURNING j.*
                    """
                ),
                {
                    "batch": batch,
                    "worker_id": worker_id,
                    "visibility_seconds": int(visibility_timeout.total_seconds()),
                },
            ).fetchall()
            return [self._row_to_job(row) for row in rows]

    def heartbeat(self, job_id: UUID, worker_id: str, visibility_timeout: timedelta) -> bool:
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE execution_jobs
                    SET lease_until=now() + (:visibility_seconds || ' seconds')::interval,
                        updated_at=now()
                    WHERE id=:job_id AND state='leased' AND leased_by=:worker_id
                    """
                ),
                {
                    "job_id": job_id,
                    "worker_id": worker_id,
                    "visibility_seconds": int(visibility_timeout.total_seconds()),
                },
            ).rowcount
            return bool(count)

    def ack_success(self, job_id: UUID, worker_id: str) -> bool:
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE execution_jobs
                    SET state='completed',
                        leased_by=NULL,
                        lease_until=NULL,
                        updated_at=now()
                    WHERE id=:job_id AND state='leased' AND leased_by=:worker_id
                    """
                ),
                {"job_id": job_id, "worker_id": worker_id},
            ).rowcount
            return bool(count)

    def release(
        self,
        job_id: UUID,
        worker_id: str,
        available_at: datetime,
        reason: str,
        decrement_attempt: bool = False,
    ) -> bool:
        attempt_expr = "GREATEST(attempt_count-1,0)" if decrement_attempt else "attempt_count"
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    f"""
                    UPDATE execution_jobs
                    SET state='queued',
                        leased_by=NULL,
                        lease_until=NULL,
                        available_at=:available_at,
                        last_error=:reason,
                        updated_at=now(),
                        attempt_count={attempt_expr}
                    WHERE id=:job_id AND state='leased' AND leased_by=:worker_id
                    """
                ),
                {
                    "job_id": job_id,
                    "worker_id": worker_id,
                    "available_at": available_at,
                    "reason": reason,
                },
            ).rowcount
            return bool(count)

    def move_to_dlq(self, job_id: UUID, worker_id: str, state: DlqState, reason: str) -> bool:
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE execution_jobs
                    SET state='dlq',
                        dlq_state=:dlq_state,
                        leased_by=NULL,
                        lease_until=NULL,
                        last_error=:reason,
                        updated_at=now()
                    WHERE id=:job_id AND state='leased' AND leased_by=:worker_id
                    """
                ),
                {"job_id": job_id, "worker_id": worker_id, "dlq_state": state.value, "reason": reason},
            ).rowcount
            if count:
                self._record_dlq_event(conn, job_id, state.value, worker_id, {"reason": reason})
            return bool(count)

    def reclaim_expired(self) -> int:
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE execution_jobs
                    SET state='queued',
                        leased_by=NULL,
                        lease_until=NULL,
                        available_at=now(),
                        updated_at=now()
                    WHERE state='leased' AND lease_until IS NOT NULL AND lease_until < now()
                    """
                )
            ).rowcount
            return int(count or 0)

    def get(self, job_id: UUID) -> Optional[ExecutionJob]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT * FROM execution_jobs WHERE id=:job_id"),
                {"job_id": job_id},
            ).first()
            return self._row_to_job(row) if row else None

    def list_dlq(self, limit: int = 100) -> List[ExecutionJob]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT *
                    FROM execution_jobs
                    WHERE state='dlq'
                    ORDER BY updated_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()
            return [self._row_to_job(row) for row in rows]

    def replay_dlq(self, job_id: UUID, actor: str) -> Optional[ExecutionJob]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT * FROM execution_jobs WHERE id=:job_id AND state='dlq' FOR UPDATE"),
                {"job_id": job_id},
            ).first()
            if not row:
                return None

            original = self._row_to_job(row)
            conn.execute(
                text(
                    """
                    UPDATE execution_jobs
                    SET dlq_state=:state, updated_at=now()
                    WHERE id=:job_id
                    """
                ),
                {"job_id": job_id, "state": DlqState.REPLAYED.value},
            )
            self._record_dlq_event(conn, job_id, "replayed", actor, {})

            new_job = ExecutionJob.new(
                intent=original.intent,
                context_domain=original.context_domain,
                reservation_delta=original.reservation_delta,
                priority=original.priority,
                max_attempts=original.max_attempts,
            )
            new_job.job_version = original.job_version + 1
            new_job.parent_job_id = original.id
            new_job.last_error = f"Replayed by {actor}"
            existing_active = conn.execute(
                text(
                    """
                    SELECT *
                    FROM execution_jobs
                    WHERE intent_id=:intent_id
                      AND state IN ('queued', 'leased')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"intent_id": new_job.intent.id},
            ).first()
            if existing_active:
                return self._row_to_job(existing_active)
            conn.execute(
                text(
                    """
                    INSERT INTO execution_jobs (
                        id, intent_id, intent_json, context_domain, reservation_delta,
                        state, priority, available_at, created_at, updated_at,
                        attempt_count, max_attempts, job_version, parent_job_id, last_error
                    ) VALUES (
                        :id, :intent_id, :intent_json::jsonb, :context_domain, :reservation_delta::jsonb,
                        :state, :priority, :available_at, :created_at, :updated_at,
                        :attempt_count, :max_attempts, :job_version, :parent_job_id, :last_error
                    )
                    """
                ),
                {
                    "id": new_job.id,
                    "intent_id": new_job.intent.id,
                    "intent_json": json.dumps(serialize_intent(new_job.intent)),
                    "context_domain": new_job.context_domain,
                    "reservation_delta": json.dumps(new_job.reservation_delta),
                    "state": new_job.state.value,
                    "priority": new_job.priority,
                    "available_at": new_job.available_at,
                    "created_at": new_job.created_at,
                    "updated_at": new_job.updated_at,
                    "attempt_count": new_job.attempt_count,
                    "max_attempts": new_job.max_attempts,
                    "job_version": new_job.job_version,
                    "parent_job_id": new_job.parent_job_id,
                    "last_error": new_job.last_error,
                },
            )
            return new_job

    def resolve_dlq(self, job_id: UUID, actor: str, state: DlqState) -> bool:
        if state not in (DlqState.TERMINAL, DlqState.RESOLVED):
            return False
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE execution_jobs
                    SET dlq_state=:state, updated_at=now()
                    WHERE id=:job_id AND state='dlq'
                    """
                ),
                {"job_id": job_id, "state": state.value},
            ).rowcount
            if count:
                self._record_dlq_event(conn, job_id, state.value, actor, {})
            return bool(count)

    def depth(self) -> int:
        with self.engine.begin() as conn:
            value = conn.execute(
                text("SELECT COUNT(*) FROM execution_jobs WHERE state='queued'")
            ).scalar_one()
            return int(value)

    def depth_by_context(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT context_domain, COUNT(*) AS cnt
                    FROM execution_jobs
                    WHERE state='queued'
                    GROUP BY context_domain
                    """
                )
            ).fetchall()
            for row in rows:
                out[row.context_domain] = int(row.cnt)
        return out

    def _record_dlq_event(self, conn, job_id: UUID, event_type: str, actor: str, payload: Dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO execution_dlq_events (id, job_id, event_type, actor, created_at, payload)
                VALUES (:id, :job_id, :event_type, :actor, :created_at, :payload::jsonb)
                """
            ),
            {
                "id": uuid4(),
                "job_id": job_id,
                "event_type": event_type,
                "actor": actor,
                "created_at": datetime.now(timezone.utc),
                "payload": json.dumps(payload or {}),
            },
        )
