from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class WorkerHeartbeat:
    worker_id: str
    updated_at: datetime
    status: str


class WorkerHeartbeatStore(ABC):
    @abstractmethod
    def beat(self, worker_id: str, status: str = "alive") -> None:
        pass

    @abstractmethod
    def stale_workers(self, timeout: timedelta) -> List[str]:
        pass


class InMemoryWorkerHeartbeatStore(WorkerHeartbeatStore):
    def __init__(self):
        self._beats: Dict[str, WorkerHeartbeat] = {}
        self._lock = Lock()

    def beat(self, worker_id: str, status: str = "alive") -> None:
        with self._lock:
            self._beats[worker_id] = WorkerHeartbeat(
                worker_id=worker_id, updated_at=datetime.now(timezone.utc), status=status
            )

    def stale_workers(self, timeout: timedelta) -> List[str]:
        cutoff = datetime.now(timezone.utc) - timeout
        with self._lock:
            return [k for k, hb in self._beats.items() if hb.updated_at < cutoff]


class PostgresWorkerHeartbeatStore(WorkerHeartbeatStore):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresWorkerHeartbeatStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS execution_worker_heartbeats (
                        worker_id TEXT PRIMARY KEY,
                        updated_at TIMESTAMPTZ NOT NULL,
                        status TEXT NOT NULL
                    )
                    """
                )
            )

    def beat(self, worker_id: str, status: str = "alive") -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO execution_worker_heartbeats(worker_id, updated_at, status)
                    VALUES (:worker_id, now(), :status)
                    ON CONFLICT (worker_id)
                    DO UPDATE SET updated_at=EXCLUDED.updated_at, status=EXCLUDED.status
                    """
                ),
                {"worker_id": worker_id, "status": status},
            )

    def stale_workers(self, timeout: timedelta) -> List[str]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT worker_id
                    FROM execution_worker_heartbeats
                    WHERE updated_at < now() - (:timeout_seconds || ' seconds')::interval
                    """
                ),
                {"timeout_seconds": int(timeout.total_seconds())},
            ).fetchall()
        return [row.worker_id for row in rows]
