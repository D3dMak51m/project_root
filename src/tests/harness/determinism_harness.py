import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from src.core.domain.entity import AIHuman
from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState
from src.core.domain.memory import MemorySystem
from src.core.domain.stance import Stance
from src.core.domain.readiness import ActionReadiness
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_context import StrategicContext
from src.core.lifecycle.signals import LifeSignals
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.time.frozen_time_source import FrozenTimeSource
from src.core.ledger.file_ledger import FileStrategicLedger
from src.core.ledger.file_budget_ledger import FileBudgetLedger
from src.core.persistence.file_backend import FileStrategicStateBackend
from src.core.persistence.budget_backend import FileBudgetBackend
from src.infrastructure.adapters.mock_execution_adapter import MockExecutionAdapter


class DeterminismTestHarness:
    """
    End-to-End Deterministic Validation Harness.
    Validates that the system state is perfectly reproducible via replay.
    Uses file-backed storage to ensure true isolation between runs.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or tempfile.mkdtemp()
        self.state_dir = os.path.join(self.base_dir, "state")
        self.budget_file = os.path.join(self.base_dir, "budget.json")
        self.ledger_file = os.path.join(self.base_dir, "ledger.jsonl")
        self.budget_ledger_file = os.path.join(self.base_dir, "budget_ledger.jsonl")

        # Setup Time
        self.start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.time_source = FrozenTimeSource(self.start_time)

        # Setup Context
        self.context = StrategicContext("global", None, None, "social_media")

    def _create_fresh_human(self) -> AIHuman:
        """
        Creates a fresh, empty AIHuman instance.
        Used for both Live start and Replay start to ensure no memory leakage.
        """
        return AIHuman(
            id=uuid4(),
            identity=Identity("TestSubject", 30, "N/A", "Test Bio", [], [], {}),
            state=BehaviorState(100.0, 100.0, 0.0, self.start_time, False),
            memory=MemorySystem([], []),
            stance=Stance({}),
            readiness=ActionReadiness(50.0, 40.0, 80.0),
            intentions=[],
            personas=[],
            # In real app, personas are config. Here empty is fine as Orchestrator handles selection logic or we add one.
            # Adding a default persona to allow execution eligibility checks to pass
            # (ExecutionEligibilityService requires a mask)
            # But wait, Orchestrator._select_mask picks from human.personas.
            # So we MUST provide a persona.
            # Let's add one.
            # Importing PersonaMask locally to avoid top-level circular issues if any
            # from src.core.domain.persona import PersonaMask
            # (Assuming imports are available)
            strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
            deferred_actions=[],
            created_at=self.start_time
        )

    def _add_persona(self, human: AIHuman):
        from src.core.domain.persona import PersonaMask
        mask = PersonaMask(
            id=uuid4(), human_id=human.id, platform="test", display_name="TestBot",
            bio="", language="en", tone="neutral", verbosity="medium",
            activity_rate=1.0, risk_tolerance=1.0, posting_hours=list(range(24))
        )
        human.personas.append(mask)

    def _create_orchestrator(self) -> StrategicOrchestrator:
        # Persistence (File-backed for isolation)
        state_backend = FileStrategicStateBackend(self.state_dir)
        budget_backend = FileBudgetBackend(self.budget_file)

        # Ledgers (File-backed for isolation)
        ledger = FileStrategicLedger(self.ledger_file)
        budget_ledger = FileBudgetLedger(self.budget_ledger_file)

        return StrategicOrchestrator(
            time_source=self.time_source,
            ledger=ledger,
            backend=state_backend,
            budget_backend=budget_backend,
            budget_ledger=budget_ledger,
            execution_adapter=MockExecutionAdapter()
        )

    def run_simulation(self, ticks: int) -> Dict[str, Any]:
        """
        Runs the system for N ticks and returns the final state snapshot.
        """
        # 1. Create fresh human
        human = self._create_fresh_human()
        self._add_persona(human)

        # 2. Create orchestrator
        orchestrator = self._create_orchestrator()
        orchestrator.register_context(self.context, human)

        # 3. Run ticks
        for i in range(ticks):
            # Advance time
            self.time_source.advance(timedelta(minutes=10))

            # Create signals (deterministic)
            # NO manual execution_feedback injection.
            # Feedback comes ONLY from the Orchestrator's internal loop via Adapter.

            signals = LifeSignals(
                pressure_delta=1.0,  # Constant pressure to drive intentions
                energy_delta=0.0,
                attention_delta=0.0,
                rest=False,
                perceived_topics={"topic_a": (0.5, 0.1)},
                memories=[],
                execution_feedback=None  # Explicitly None, let Orchestrator handle it
            )

            orchestrator.tick(human, signals)

        # 4. Capture State
        runtime = orchestrator._runtimes[str(self.context)]
        snapshot = runtime.lifeloop.get_strategic_snapshot(human, self.context)
        budget_snapshot = orchestrator._budget

        return {
            "snapshot": snapshot,
            "budget": budget_snapshot,
            "tick_count": runtime.tick_count
        }

    def run_replay(self) -> Dict[str, Any]:
        """
        Simulates a restart and replay.
        """
        # 1. Create NEW fresh human (Clean slate)
        human = self._create_fresh_human()
        self._add_persona(human)

        # 2. Create NEW orchestrator instance (Simulating restart)
        # It will read from the SAME files created by run_simulation
        orchestrator = self._create_orchestrator()

        # 3. Register context triggers restore() -> replay()
        # This loads snapshot and replays events from file ledgers
        orchestrator.register_context(self.context, human)

        runtime = orchestrator._runtimes[str(self.context)]

        # 4. Capture Restored State
        snapshot = runtime.lifeloop.get_strategic_snapshot(human, self.context)
        budget_snapshot = orchestrator._budget

        return {
            "snapshot": snapshot,
            "budget": budget_snapshot,
            "tick_count": runtime.tick_count
        }

    def compare_states(self, state_a: Dict[str, Any], state_b: Dict[str, Any]) -> bool:
        """
        Compares two state dictionaries for equality.
        """
        snap_a = state_a["snapshot"]
        snap_b = state_b["snapshot"]

        # Compare Strategic Snapshot Fields
        if snap_a.mode != snap_b.mode:
            print(f"MISMATCH: Mode {snap_a.mode} != {snap_b.mode}")
            return False
        if snap_a.confidence != snap_b.confidence:
            print(f"MISMATCH: Confidence {snap_a.confidence} != {snap_b.confidence}")
            return False

        # Compare Trajectories
        if len(snap_a.active_trajectories) != len(snap_b.active_trajectories):
            print("MISMATCH: Active trajectory count differs")
            return False

        # Compare Budget
        bud_a = state_a["budget"]
        bud_b = state_b["budget"]

        # Compare timestamps (ISO format equality)
        if bud_a.last_updated.isoformat() != bud_b.last_updated.isoformat():
            print(f"MISMATCH: Budget timestamp {bud_a.last_updated} != {bud_b.last_updated}")
            return False

        if bud_a.energy_budget != bud_b.energy_budget:
            print(f"MISMATCH: Budget energy {bud_a.energy_budget} != {bud_b.energy_budget}")
            return False

        return True

    def cleanup(self):
        shutil.rmtree(self.base_dir)