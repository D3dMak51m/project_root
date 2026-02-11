import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.hierarchy.domain.hierarchy_models import HierarchyDirective, directive_from_payload


class PostgresHierarchyOverrideStore:
    """
    Persistent runtime overrides for hierarchy directives.
    """

    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresHierarchyOverrideStore":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS hierarchy_overrides (
                        id UUID PRIMARY KEY,
                        level TEXT NOT NULL,
                        target TEXT NOT NULL,
                        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        active BOOLEAN NOT NULL DEFAULT TRUE,
                        actor TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        deactivated_at TIMESTAMPTZ NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_hierarchy_overrides_active_level
                    ON hierarchy_overrides (active, level)
                    """
                )
            )

    def create_override(
        self,
        level: str,
        target: str,
        payload: Dict,
        actor: str,
    ) -> UUID:
        now = datetime.now(timezone.utc)
        row_id = uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO hierarchy_overrides (
                        id, level, target, payload, active, actor, created_at
                    ) VALUES (
                        :id, :level, :target, :payload::jsonb, TRUE, :actor, :created_at
                    )
                    """
                ),
                {
                    "id": row_id,
                    "level": level,
                    "target": target,
                    "payload": json.dumps(payload or {}),
                    "actor": actor,
                    "created_at": now,
                },
            )
        return row_id

    def deactivate_override(self, override_id: UUID) -> bool:
        with self.engine.begin() as conn:
            count = conn.execute(
                text(
                    """
                    UPDATE hierarchy_overrides
                    SET active=FALSE, deactivated_at=now()
                    WHERE id=:id AND active=TRUE
                    """
                ),
                {"id": override_id},
            ).rowcount
            return bool(count)

    def list_active(self) -> List[HierarchyDirective]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, level, target, payload, created_at
                    FROM hierarchy_overrides
                    WHERE active=TRUE
                    ORDER BY created_at ASC
                    """
                )
            ).fetchall()
        return [self._to_directive(row) for row in rows]

    def get(self, override_id: UUID) -> Optional[HierarchyDirective]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, level, target, payload, created_at
                    FROM hierarchy_overrides
                    WHERE id=:id
                    LIMIT 1
                    """
                ),
                {"id": override_id},
            ).first()
        return self._to_directive(row) if row else None

    def _to_directive(self, row) -> HierarchyDirective:
        payload = dict(row.payload or {})
        payload["id"] = str(row.id)
        payload["level"] = row.level
        payload["target"] = row.target
        payload["created_at"] = row.created_at
        return directive_from_payload(payload)

