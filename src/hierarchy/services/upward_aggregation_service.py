import json
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.domain.execution_result import ExecutionResult, ExecutionStatus
from src.hierarchy.domain.hierarchy_models import HierarchyLevel


@dataclass(frozen=True)
class AggregatePoint:
    bucket_at: datetime
    level: HierarchyLevel
    key: str
    metrics: Dict[str, float]


class UpwardAggregationService:
    """
    Aggregates execution and counterfactual signals upward (L2 -> L1 -> L0).
    """

    def __init__(self, engine: Optional[Engine] = None, bucket_seconds: int = 60):
        self.engine = engine
        self.bucket_seconds = max(10, int(bucket_seconds))
        self._mem: Dict[Tuple[str, str, str], Dict[str, float]] = {}
        self._lock = Lock()
        if self.engine:
            self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str, bucket_seconds: int = 60) -> "UpwardAggregationService":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine=engine, bucket_seconds=bucket_seconds)

    def ensure_schema(self) -> None:
        if not self.engine:
            return
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS hierarchy_aggregates (
                        bucket_at TIMESTAMPTZ NOT NULL,
                        level TEXT NOT NULL,
                        key TEXT NOT NULL,
                        metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                        PRIMARY KEY (bucket_at, level, key)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_hierarchy_aggregates_level_key_bucket
                    ON hierarchy_aggregates (level, key, bucket_at DESC)
                    """
                )
            )

    def record_execution(
        self,
        context_domain: str,
        result: ExecutionResult,
        reservation_delta: Optional[Dict[str, float]] = None,
        queue_lag: float = 0.0,
    ) -> None:
        reservation_delta = dict(reservation_delta or {})
        pressure = sum(abs(v) for v in reservation_delta.values() if v < 0)
        failed = 1.0 if result.status in (ExecutionStatus.FAILED, ExecutionStatus.REJECTED) else 0.0

        metrics = {
            "execution_total": 1.0,
            "execution_failed": failed,
            "budget_pressure": pressure,
            "queue_lag": float(queue_lag),
        }
        self._record_for_domain(context_domain, metrics)

    def record_counterfactual(self, context_domain: str, stage: str, reason: str) -> None:
        metrics = {
            "counterfactual_total": 1.0,
            f"counterfactual_stage:{stage}": 1.0,
        }
        if reason:
            metrics[f"counterfactual_reason:{reason}"] = 1.0
        self._record_for_domain(context_domain, metrics)

    def list_aggregates(self, level: Optional[HierarchyLevel] = None, limit: int = 200) -> List[AggregatePoint]:
        if self.engine:
            return self._list_from_db(level=level, limit=limit)
        with self._lock:
            points: List[AggregatePoint] = []
            for (bucket, raw_level, key), metrics in self._mem.items():
                lv = HierarchyLevel(raw_level)
                if level and lv != level:
                    continue
                points.append(
                    AggregatePoint(
                        bucket_at=datetime.fromisoformat(bucket),
                        level=lv,
                        key=key,
                        metrics=dict(metrics),
                    )
                )
            points.sort(key=lambda x: x.bucket_at, reverse=True)
            return points[:limit]

    def _record_for_domain(self, context_domain: str, metrics: Dict[str, float]) -> None:
        parts = context_domain.split(":", 1)
        platform_key = parts[0] if parts else "unknown"
        rows = [
            (HierarchyLevel.L2, context_domain),
            (HierarchyLevel.L1, platform_key),
            (HierarchyLevel.L0, "global"),
        ]
        for level, key in rows:
            self._increment(level, key, metrics)

    def _bucket(self, now: datetime) -> datetime:
        ts = int(now.timestamp())
        bucket = ts - (ts % self.bucket_seconds)
        return datetime.fromtimestamp(bucket, tz=timezone.utc)

    def _increment(self, level: HierarchyLevel, key: str, metrics: Dict[str, float]) -> None:
        now = datetime.now(timezone.utc)
        bucket = self._bucket(now)
        if self.engine:
            self._increment_db(bucket, level, key, metrics)
            return

        mem_key = (bucket.isoformat(), level.value, key)
        with self._lock:
            slot = self._mem.setdefault(mem_key, {})
            for metric_key, value in metrics.items():
                slot[metric_key] = float(slot.get(metric_key, 0.0)) + float(value)

    def _increment_db(self, bucket: datetime, level: HierarchyLevel, key: str, metrics: Dict[str, float]) -> None:
        assert self.engine is not None
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT metrics_json
                    FROM hierarchy_aggregates
                    WHERE bucket_at=:bucket_at AND level=:level AND key=:key
                    FOR UPDATE
                    """
                ),
                {"bucket_at": bucket, "level": level.value, "key": key},
            ).first()
            base = dict(row.metrics_json or {}) if row else {}
            for metric_key, value in metrics.items():
                base[metric_key] = float(base.get(metric_key, 0.0)) + float(value)
            conn.execute(
                text(
                    """
                    INSERT INTO hierarchy_aggregates (bucket_at, level, key, metrics_json)
                    VALUES (:bucket_at, :level, :key, :metrics_json::jsonb)
                    ON CONFLICT (bucket_at, level, key)
                    DO UPDATE SET metrics_json=:metrics_json::jsonb
                    """
                ),
                {
                    "bucket_at": bucket,
                    "level": level.value,
                    "key": key,
                    "metrics_json": json.dumps(base),
                },
            )

    def _list_from_db(self, level: Optional[HierarchyLevel], limit: int) -> List[AggregatePoint]:
        assert self.engine is not None
        where = ""
        params: Dict[str, object] = {"limit": limit}
        if level:
            where = "WHERE level=:level"
            params["level"] = level.value
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT bucket_at, level, key, metrics_json
                    FROM hierarchy_aggregates
                    {where}
                    ORDER BY bucket_at DESC
                    LIMIT :limit
                    """
                ),
                params,
            ).fetchall()
        return [
            AggregatePoint(
                bucket_at=row.bucket_at,
                level=HierarchyLevel(row.level),
                key=row.key,
                metrics=dict(row.metrics_json or {}),
            )
            for row in rows
        ]

