from typing import Optional
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.domain.budget_snapshot import BudgetSnapshot
from src.core.domain.resource import StrategicResourceBudget
from src.core.persistence.budget_backend import BudgetPersistenceBackend


class PostgresBudgetBackend(BudgetPersistenceBackend):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.ensure_schema()

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresBudgetBackend":
        engine = create_engine(dsn, pool_pre_ping=True, future=True)
        return cls(engine)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS budget_snapshots (
                        id UUID PRIMARY KEY,
                        snapshot_at TIMESTAMPTZ NOT NULL,
                        energy_budget DOUBLE PRECISION NOT NULL,
                        attention_budget DOUBLE PRECISION NOT NULL,
                        execution_slots INTEGER NOT NULL,
                        last_updated TIMESTAMPTZ NOT NULL,
                        energy_recovery_rate DOUBLE PRECISION NOT NULL,
                        attention_recovery_rate DOUBLE PRECISION NOT NULL,
                        slot_recovery_rate DOUBLE PRECISION NOT NULL,
                        last_event_id UUID NULL,
                        version TEXT NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_budget_snapshots_snapshot_at
                    ON budget_snapshots (snapshot_at DESC)
                    """
                )
            )

    def load(self) -> Optional[BudgetSnapshot]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT *
                    FROM budget_snapshots
                    ORDER BY snapshot_at DESC
                    LIMIT 1
                    """
                )
            ).first()
        if not row:
            return None
        budget = StrategicResourceBudget(
            energy_budget=float(row.energy_budget),
            attention_budget=float(row.attention_budget),
            execution_slots=int(row.execution_slots),
            last_updated=row.last_updated,
            energy_recovery_rate=float(row.energy_recovery_rate),
            attention_recovery_rate=float(row.attention_recovery_rate),
            slot_recovery_rate=float(row.slot_recovery_rate),
        )
        return BudgetSnapshot(
            budget=budget,
            timestamp=row.snapshot_at,
            last_event_id=row.last_event_id,
            version=row.version,
        )

    def save(self, snapshot: BudgetSnapshot) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO budget_snapshots (
                        id,
                        snapshot_at,
                        energy_budget,
                        attention_budget,
                        execution_slots,
                        last_updated,
                        energy_recovery_rate,
                        attention_recovery_rate,
                        slot_recovery_rate,
                        last_event_id,
                        version
                    )
                    VALUES (
                        :id,
                        :snapshot_at,
                        :energy_budget,
                        :attention_budget,
                        :execution_slots,
                        :last_updated,
                        :energy_recovery_rate,
                        :attention_recovery_rate,
                        :slot_recovery_rate,
                        :last_event_id,
                        :version
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "snapshot_at": snapshot.timestamp,
                    "energy_budget": snapshot.budget.energy_budget,
                    "attention_budget": snapshot.budget.attention_budget,
                    "execution_slots": snapshot.budget.execution_slots,
                    "last_updated": snapshot.budget.last_updated,
                    "energy_recovery_rate": snapshot.budget.energy_recovery_rate,
                    "attention_recovery_rate": snapshot.budget.attention_recovery_rate,
                    "slot_recovery_rate": snapshot.budget.slot_recovery_rate,
                    "last_event_id": snapshot.last_event_id,
                    "version": snapshot.version,
                },
            )
